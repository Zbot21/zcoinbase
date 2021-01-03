import configparser

from absl import app

from zcoinbase.authenticated_client import AuthenticatedClient
from zcoinbase.util import OrderSide, OrderStatus, ReportType


SANDBOX_REST = 'https://api-public.sandbox.pro.coinbase.com'


# Basic example of auth API, SHOULD ONLY BE USED WITH SANDBOX API.
# DO NOT USE THIS ON THE PROD API OR YOU WILL LOSE MONEY!!
def main(argv):
  config = configparser.ConfigParser()
  config.read('coinbase_sandbox.ini')
  auth_client = AuthenticatedClient(api_key=config['Coinbase']['api_key'],
                                    api_secret=config['Coinbase']['api_secret'],
                                    passphrase=config['Coinbase']['passphrase'],
                                    rest_url=SANDBOX_REST)
  time = auth_client.get_time()
  print(time)
  # Print all non-zero accounts.
  non_zero_accounts = [account for account in auth_client.get_all_accounts() if float(account['available']) != 0]
  print(non_zero_accounts)
  # Figure out what currencies we have, and in what amounts.
  available_currencies = [{account['currency']: account['balance']} for account in non_zero_accounts]
  print(available_currencies)
  # Buy some bitcoin
  print(auth_client.market_order(side=OrderSide.BUY, product_id='BTC-USD', funds=100))
  print(list(auth_client.list_orders(status=[OrderStatus.OPEN], product_id='BTC-USD')))
  print(list(auth_client.list_fills(product_id='BTC-USD')))
  report = auth_client.generate_report(ReportType.FILLS, '2021-01-01', time['iso'], product_id='BTC-USD')
  print(report)
  report_status = auth_client.get_report_status(report['id'])
  print(report_status)


if __name__ == '__main__':
  app.run(main)
