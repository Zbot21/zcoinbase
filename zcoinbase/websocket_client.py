import websocket
import json
import logging
import threading

from .util import LogLevel

# Special Channels that are not used by coinbase, but are internal to connecting and disconnecting from coinbase.
SPECIAL_CHANNELS = ['error', 'close', 'open', 'subscriptions']


# TODO: Support Authenticated Websocket
# noinspection PyUnusedLocal
class CoinbaseWebsocket:
  def __init__(self, websocket_addr='wss://ws-feed-public.sandbox.pro.coinbase.com',
               products_to_listen=None,
               channels_to_function=None,
               preparse_json=True,
               autostart=True,
               log_level=LogLevel.BASIC_MESSAGES):
    """Constructor for the CoinbaseWebsocket.

    Minimal Usage:
      # This will subscribe to the heartbeat channel and print all messages on the websocket.
      cbws = CoinbaseWebsocket(products_to_listen='BTC-USD',
                               channels_to_function={'heartbeat': lambda msg: print(msg) })

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
          "close": Handle on-close (parameter is websocket)
          "open": Handle on-open (parameter is websocket)
      preparse_json: (Default: True) Should we pass json to channels to function or simply the string?
      autostart: (Default: True) Start the websocket by default.
      log_level: (Default: ERROR_LOG) The LOG_LEVEL to use for this class, by default, will only report errors (using
        python logging api)
    """
    if products_to_listen is None:
      products_to_listen = []
    if channels_to_function is None:
      channels_to_function = {}
    self.websocket_addr = websocket_addr
    self.products_to_listen = products_to_listen
    self.channels_to_function = channels_to_function
    self.preparse_json = preparse_json
    self.log_level = log_level
    self.ws = websocket.WebSocketApp(self.websocket_addr,
                                     on_message=lambda ws, msg: self.on_message(ws, msg),
                                     on_error=lambda ws, err: self.on_error(ws, err),
                                     on_close=lambda ws: self.on_close(ws),
                                     on_open=lambda ws: self.on_open(ws))
    if autostart:
      self.ws_thread = threading.Thread(target=self.start_websocket)
      self.ws_thread.start()

  def __del__(self):
    self.close_websocket()

  def start_websocket(self):
    self.ws.run_forever()

  def close_websocket(self):
    self.ws.close()

  @staticmethod
  def make_subscribe(product_ids=None, channels=None):
    if product_ids is None or channels is None:
      raise SyntaxError('Must specify channels and product_ids')
    subscribe_msg = json.dumps({'type': 'subscribe', 'product_ids': product_ids, 'channels': channels})
    print(subscribe_msg)
    return subscribe_msg

  def add_channel_function(self, channel, function, refresh_subscriptions=True):
    self.channels_to_function[channel] = function
    if refresh_subscriptions:
      self.subscribe()

  def add_product(self, product, refresh_subscriptions=True):
    self.products_to_listen.append(product)
    if refresh_subscriptions:
      self.subscribe()

  def subscribe(self):
    self.ws.send(CoinbaseWebsocket.make_subscribe(self.products_to_listen,
                                                  [channel for channel in self.channels_to_function.keys() if
                                                   channel not in SPECIAL_CHANNELS]))

  def on_open(self, ws):
    if self.log_level >= LogLevel.BASIC_MESSAGES:
      logging.info('Coinbase Websocket Connection ({})'.format(self.websocket_addr))
    # Subscribe to defaults.
    if self.products_to_listen and self.channels_to_function:
      self.subscribe()
    if 'open' in self.channels_to_function:
      self.channels_to_function['open'](ws)

  def on_error(self, ws, err):
    del ws  # We don't use this, but it's required by WebSocketApp.
    if self.log_level >= LogLevel.ERROR_LOG:
      logging.error('Error Received: {}'.format(err))
    if 'error' in self.channels_to_function:
      self.channels_to_function['error'](json.loads(err) if self.preparse_json else err)

  def on_message(self, ws, message):
    del ws  # We don't use this, but it's required by WebSocketApp.
    if self.log_level >= LogLevel.VERBOSE_LOG:
      logging.info('Message Received: {}'.format(message))
    json_msg = json.loads(message)
    if 'type' in json_msg and json_msg['type'] in self.channels_to_function:
      self.channels_to_function[json_msg['type']](json_msg if self.preparse_json else message)

  def on_close(self, ws):
    if self.log_level >= LogLevel.BASIC_MESSAGES:
      logging.info('Coinbase Websocket Disconnection ({})'.format(self.websocket_addr))
    if 'close' in self.channels_to_function:
      self.channels_to_function['close'](ws)
