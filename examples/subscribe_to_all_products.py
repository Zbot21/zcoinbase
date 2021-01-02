import time

from absl import app

from zcoinbase.websocket_client import CoinbaseWebsocket
from zcoinbase.public_client import PublicClient


SANDBOX_REST = 'https://api-public.sandbox.pro.coinbase.com'
SANDBOX_WEBSOCKET = 'wss://ws-feed-public.sandbox.pro.coinbase.com'


# This is a simple program that subscribes to all messages on the websocket.
# It uses the Public REST API to get a list of all the products and echos heartbeats.
def main(argv):
  del argv  # Unused
  cb = PublicClient(rest_url=SANDBOX_REST)
  products = cb.get_products()
  product_ids = [product['id'] for product in products]
  cbws = CoinbaseWebsocket(
    websocket_addr=SANDBOX_WEBSOCKET,
    products_to_listen=product_ids,
    channels_to_function={'heartbeat': lambda msg: print('hb: {}'.format(msg))},
    preparse_json=False
  )
  time.sleep(10)
  cbws.close_websocket()


if __name__ == '__main__':
  app.run(main)
