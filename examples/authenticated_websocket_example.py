import configparser
import time

from absl import app

from zcoinbase import CoinbaseWebsocket, AuthenticatedClient, OrderSide, LogLevel

SANDBOX_REST = 'https://api-public.sandbox.pro.coinbase.com'
SANDBOX_WEBSOCKET = 'wss://ws-feed-public.sandbox.pro.coinbase.com'


def main(argv):
  del argv  # Unused
  config = configparser.ConfigParser()
  config.read('coinbase_sandbox.ini')
  cb_ws = CoinbaseWebsocket(
    websocket_addr=SANDBOX_WEBSOCKET,
    products_to_listen=['BTC-USD'],
    channels_to_function={
      'ticker': lambda msg: print('ticker: {}'.format(msg)),  # Subscribe to "ticker" to see ticker.
      'subscriptions': lambda msg: print('subscriptions: {}'.format(msg)),  # Subscriptions
      'full': lambda msg: print('full: {}'.format(msg)),  # Subscribe to "full" channel to see private stuff.
      'received': lambda msg: print('rx: {}'.format(msg)),  # Subscribe to "received" channel to show that orders work.
      'all_messages': lambda msg: print('all: {}'.format(msg)),  # "all_messages" on the channel
      'error': lambda msg: print('error: {}'.format(msg))
    },
    log_level=LogLevel.VERBOSE_LOG,
    api_key=config['Coinbase']['api_key'],
    api_secret=config['Coinbase']['api_secret'],
    passphrase=config['Coinbase']['passphrase'],
  )
  auth_client = AuthenticatedClient(api_key=config['Coinbase']['api_key'],
                                    api_secret=config['Coinbase']['api_secret'],
                                    passphrase=config['Coinbase']['passphrase'],
                                    rest_url=SANDBOX_REST)
  time.sleep(5)
  buy_order_result = auth_client.market_order(side=OrderSide.BUY, product_id='BTC-USD', funds=100)
  print('BUY ORDER: {}'.format(buy_order_result))
  time.sleep(5)
  # Wait for the buy order to complete.
  while auth_client.get_order(order_id=buy_order_result['id'])['status'] != 'done':
    time.sleep(1)
  order_status = auth_client.get_order(order_id=buy_order_result['id'])
  sell_order_result = auth_client.market_order(side=OrderSide.SELL, product_id='BTC-USD',
                                               size=order_status['filled_size'])
  print('SELL ORDER: {}'.format(sell_order_result))
  while auth_client.get_order(order_id=sell_order_result['id'])['status'] != 'done':
    time.sleep(1)
  time.sleep(5)
  cb_ws.close_websocket()


if __name__ == '__main__':
  app.run(main)
