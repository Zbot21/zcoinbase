import websocket
import json
import logging
import threading

from typing import Text, Callable

from .util import LogLevel
from .coinbase_auth import CoinbaseAuth

# Special channels are sometimes sent by Coinbase, but cannot be subscribed to directly.
SPECIAL_CHANNELS = ['error',
                    # Do an action when the websocket is opened/closed.
                    # The parameters for these functions will be the websocket.
                    'open_websocket',
                    'close_websocket',
                    # All Messages.
                    'all_messages',
                    # Sent when new subscriptions are created. Docs: https://docs.pro.coinbase.com/#subscribe
                    'subscriptions',
                    # Used by Coinbase "level2" channel, allowing you to keep a snapshot of the order-book locally.
                    # Documentation: https://docs.pro.coinbase.com/#the-level2-channel
                    'snapshot',
                    'l2update',
                    ]
# Channels received with "full" subscription: https://docs.pro.coinbase.com/#the-full-channel
FULL_CHANNELS = ['open', 'received', 'match', 'change', 'activate']


# noinspection PyUnusedLocal
class CoinbaseWebsocket:
  PROD_ADDRESS = 'wss://ws-feed.pro.coinbase.com'
  SANDBOX_ADDRESS = 'wss://ws-feed-public.sandbox.pro.coinbase.com'

  def __init__(self, websocket_addr=PROD_ADDRESS,
               products_to_listen: list[Text] = None,
               channels_to_function: dict[Text, list[Callable]] = None,
               extra_channels: list[Text] = None,
               preparse_json: bool = True,
               autostart: bool = True,
               log_level: LogLevel = LogLevel.BASIC_MESSAGES,
               api_key=None, api_secret=None, passphrase=None):
    """Constructor for the CoinbaseWebsocket.

    Minimal Usage:
      # This will subscribe to the heartbeat channel and print all messages on the websocket.
      cbws = CoinbaseWebsocket(products_to_listen='BTC-USD',
                               channels_to_function={'heartbeat': lambda msg: print(msg) })

    You can also add a list of functions to run on each channel. Using add_channel_function will add
    a new function to the list.

    All three api_key, api_secret, and passphrase are required for authenticated websocket.

    Args:
      websocket_addr: The address to subscribe to. Default is prod, but you should use Sandbox for testing.
        Sandbox: 'wss://ws-feed-public.sandbox.pro.coinbase.com'
        Prod: 'wss://ws-feed-public.sandbox.pro.coinbase.com'
      products_to_listen: List of products to subscribe to when the socket is initially opened.
        Be warned, if you don't subscribe to something within 5 seconds of opening, the Websocket will be closed, you
        can call start_websocket to restart the websocket, but you're responsible for the threading that this class
        takes care of for you normally (if autostart is True)
      channels_to_function: Map of Channels to Functions, functions should take a single parameter (the message is
        parsed json, unless preparse_json is False).
        These functions will be called any time we get a message for a given channel.
        "Special" Channels:
          "error": Error Handler (gets json or string message)
          "close_websocket": Handle on-close (parameter is websocket)
          "open_websocket": Handle on-open (parameter is websocket)
          "full": Subscribing to this channel will create FULL_CHANNELS messages.
                  These messages might be useful for authenticated clients for confirming filling of orders.
      extra_channels: Extra channels to subscribe to without a function.
      preparse_json: (Default: True) Should we pass json to channels to function or simply the string?
      autostart: (Default: True) Start the websocket by default.
      log_level: (Default: ERROR_LOG) The LOG_LEVEL to use for this class, by default, will only report errors (using
        python logging api)
      api_key: (optional) API Key for Authenticated Websocket
      api_secret: (optional) API Secret for Authenticated Websocket
      passphrase: (optional) passphrase for authenticated websocket
    """
    if products_to_listen is None:
      products_to_listen = []
    if channels_to_function is None:
      channels_to_function = {}
    if extra_channels is None:
      extra_channels = []
    self.websocket_addr = websocket_addr
    self.products_to_listen = products_to_listen
    self.channels_to_function = channels_to_function
    self.extra_channels = extra_channels
    self.preparse_json = preparse_json
    self.log_level = log_level
    self.api_key = api_key
    self.api_secret = api_secret
    self.passphrase = passphrase
    self.ws = websocket.WebSocketApp(self.websocket_addr,
                                     on_message=lambda ws, msg: self.on_message(ws, msg),
                                     on_error=lambda ws, err: self.on_error(ws, err),
                                     on_close=lambda ws: self.on_close(ws),
                                     on_open=lambda ws: self.on_open(ws))
    if autostart:
      self.ws_thread = threading.Thread(target=self.start_websocket, daemon=True)
      self.ws_thread.start()

  def __del__(self):
    self.close_websocket()

  def start_websocket(self):
    self.ws.run_forever()

  def start_websocket_in_thread(self):
    self.ws_thread = threading.Thread(target=self.start_websocket, daemon=True)
    self.ws_thread.start()

  def close_websocket(self):
    self.ws.close()

  @staticmethod
  def make_subscribe(product_ids=None, channels=None,
                     api_key=None, api_secret=None, passphrase=None):
    if product_ids is None or channels is None:
      raise SyntaxError('Must specify channels and product_ids')
    subscribe_msg = {'type': 'subscribe', 'product_ids': product_ids, 'channels': channels}
    if api_key and api_secret and passphrase:
      subscribe_msg.update(CoinbaseAuth.get_websocket_verification(api_key, api_secret, passphrase))
    return json.dumps(subscribe_msg)

  def add_channel_function(self, channel, function, refresh_subscriptions=None):
    if channel in self.channels_to_function:
      functions = self.channels_to_function[channel]
      if isinstance(functions, list):
        # Already a list, just append.
        functions.append(function)
      else:
        # Not a list, make it a list.
        current_function = functions
        functions = [current_function, function]
    else:
      self.channels_to_function[channel] = [function]
      # This is a new channel, so force subscription update, if not set.
      if refresh_subscriptions is None:
        refresh_subscriptions = True
    # Force refresh subscriptions if not explicitly set.
    if refresh_subscriptions or refresh_subscriptions is None:
      self.subscribe()

  def add_product(self, product, refresh_subscriptions=True):
    if product not in self.products_to_listen:
      self.products_to_listen.append(product)
      if refresh_subscriptions:
        self.subscribe()

  def add_channel(self, channel, refresh_subscriptions=True):
    self.extra_channels.append(channel)

  def add_authentication(self, api_key, api_secret, passphrase):
    self.api_key = api_key
    self.api_secret = api_secret
    self.passphrase = passphrase
    self.subscribe()

  def subscribe(self):
    channels = [channel for channel in self.channels_to_function.keys() if
                channel not in SPECIAL_CHANNELS + FULL_CHANNELS] + self.extra_channels
    if self.log_level >= LogLevel.VERBOSE_LOG:
      logging.info("Subscribing to channels: {}".format(", ".join(channels)))
    # Make sure there are channels and products to listen to.
    if channels and self.products_to_listen:
      self.ws.send(CoinbaseWebsocket.make_subscribe(self.products_to_listen,
                                                    channels,
                                                    self.api_key, self.api_secret, self.passphrase))

  def on_open(self, ws):
    if self.log_level >= LogLevel.BASIC_MESSAGES:
      logging.info('Coinbase Websocket Connection ({})'.format(self.websocket_addr))
    # Subscribe to defaults.
    if self.products_to_listen and self.channels_to_function:
      self.subscribe()
    if 'open_websocket' in self.channels_to_function:
      self._execute_functions_on_message(ws, self._get_functions_as_list('open_websocket'))

  def on_error(self, ws, err):
    del ws  # We don't use this, but it's required by WebSocketApp.
    if self.log_level >= LogLevel.ERROR_LOG:
      logging.error('Error Received: {}'.format(err))
    self._call_message_functions(err)

  def on_message(self, ws, message):
    del ws  # We don't use this, but it's required by WebSocketApp.
    if self.log_level >= LogLevel.VERBOSE_LOG:
      logging.info('Message Received: {}'.format(message))
    self._call_message_functions(message)

  def on_close(self, ws):
    if self.log_level >= LogLevel.BASIC_MESSAGES:
      logging.info('Coinbase Websocket Disconnection ({})'.format(self.websocket_addr))
    if 'close_websocket' in self.channels_to_function:
      self._execute_functions_on_message(ws, self._get_functions_as_list('close_websocket'))

  def _call_message_functions(self, message):
    json_msg = json.loads(message)
    functions_to_execute = list()
    if 'type' in json_msg:
      if json_msg['type'] in self.channels_to_function:
        functions_to_execute.extend(self._get_functions_as_list(json_msg['type']))
      # Subscribe to "full" messages with "full" keyword.
      if 'full' in self.channels_to_function and json_msg['type'] in FULL_CHANNELS:
        functions_to_execute.extend(self._get_functions_as_list('full'))
      # Matches messages come on "match" messages.
      if 'matches' in self.channels_to_function and json_msg['type'] == 'match':
        functions_to_execute.extend(self._get_functions_as_list('matches'))
    if 'all_messages' in self.channels_to_function:
      functions_to_execute.extend(self._get_functions_as_list('all_messages'))
    self._execute_functions_on_message(message, functions_to_execute, json_msg)

  def _execute_functions_on_message(self, message, functions, json_msg=None):
    message_is_string = isinstance(message, str)
    if json_msg is None and message_is_string:
      json_msg = json.loads(message)
    for function in functions:
      function(json_msg if self.preparse_json and message_is_string else message)

  def _get_functions_as_list(self, message_type):
    functions_list = []
    functions = self.channels_to_function[message_type]
    if isinstance(functions, list):
      functions_list.extend(functions)
    else:
      functions_list.append(functions)
    return functions_list
