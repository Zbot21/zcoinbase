import time

from absl import app

from zcoinbase.websocket_client import CoinbaseWebsocket
from zcoinbase.util import LogLevel


def main(argv):
  del argv  # Unused
  cbws = CoinbaseWebsocket(
    websocket_addr='wss://ws-feed-public.sandbox.pro.coinbase.com',  # Coinbase Sandbox
    products_to_listen=['BTC-USD'],  # Listen to BTC-USD
    channels_to_function={'heartbeat': lambda msg: print('hb: {}'.format(msg)),
                          'ticker': lambda msg: print('ticker: {}'.format(msg))},
    preparse_json=False,  # Get Strings so they print right.
    log_level=LogLevel.VERBOSE_LOG  # Log Everything!
  )
  time.sleep(10)  # Keep everything alive for 10 seconds
  cbws.close_websocket()  # Close the websocket (not required, best practice)


if __name__ == '__main__':
  app.run(main)
