import json
import uuid

from .coinbase_auth import CoinbaseAuth
from .public_client import PublicClient
from .util import OrderSide, TimeInForce, SelfTradePrevention, Stop, OrderStatus, TransferType, ReportType, ReportFormat


class AuthenticatedClient(PublicClient):
  def __init__(self, api_key, api_secret, passphrase,
               rest_url='https://api.pro.coinbase.com'):
    super().__init__(rest_url)
    self.auth = CoinbaseAuth(api_key, api_secret, passphrase)

  def get_all_accounts(self):
    """List all accounts.

    https://docs.pro.coinbase.com/#list-accounts
    """
    return self._send_get('accounts')

  def get_account(self, account_id):
    """Information for a single account.

    https://docs.pro.coinbase.com/#get-an-account
    """
    return self._send_get('accounts/{}'.format(account_id))

  def get_account_history(self, account_id):
    """Gets your account history.

    https://docs.pro.coinbase.com/#get-account-history
    """
    return self._send_paginated_get(self, 'accounts/{}/ledger'.format(account_id))

  def get_account_holds(self, account_id):
    """Gets holds on your account.

    https://docs.pro.coinbase.com/#get-holds
    """
    return self._send_paginated_get(self, 'accounts/{}/holds'.format(account_id))

  @staticmethod
  def make_order_uuid():
    return str(uuid.uuid4())

  def limit_order(self, side: OrderSide, product_id, price, size,
                  time_in_force=TimeInForce.GOOD_TILL_CANCEL,
                  cancel_after=None, post_only=None,
                  self_trade_prevention=SelfTradePrevention.DECREASE_AND_CANCEL,
                  stop=Stop.NONE, stop_price=None):
    """Places a limit order.

    https://docs.pro.coinbase.com/#place-a-new-order
    """
    if time_in_force is TimeInForce.GOOD_UNTIL_TIME and cancel_after is None:
      raise ValueError('cancel_after is required with GOOD_UNTIL_TIME')
    if cancel_after is not None and time_in_force is not TimeInForce.GOOD_UNTIL_TIME:
      raise ValueError('cannot set cancel after for orders other than GOOD_UNTIL_TIME')
    if post_only is not None and \
        (time_in_force is TimeInForce.IMMEDIATE_OR_CANCEL or time_in_force is TimeInForce.FILL_OR_KILL):
      raise ValueError('cannot set post_only with IMMEDIATE_OR_CANCEL or FILL_OR_KILL')
    if stop is not Stop.NONE and stop_price is None:
      raise ValueError('stop_price is required with LOSS or ENTRY')

    params = {
      'type': 'limit',
      'client_oid': AuthenticatedClient.make_order_uuid(),
      'side': 'buy' if side == OrderSide.BUY else 'sell',
      'price': price,
      'size': size,
      'product_id': product_id,
      'time_in_force': time_in_force.value,
      'stp': self_trade_prevention.value
    }
    if cancel_after is not None:
      params['cancel_after'] = cancel_after
    if post_only is not None:
      params['post_only'] = post_only
    if stop is not Stop.NONE:
      params['stop'] = stop.value
      params['stop_price'] = stop_price
    response = self._send_post('orders', params=params)
    response['client_oid'] = params['client_oid']
    return response

  def market_order(self, side: OrderSide, product_id, size=None, funds=None,
                   self_trade_prevention=SelfTradePrevention.DECREASE_AND_CANCEL,
                   stop=Stop.NONE, stop_price=None):
    """Places a market Order.

    https://docs.pro.coinbase.com/#place-a-new-order
    """
    if size is None and funds is None:
      raise ValueError('must specify size or funds for market order.')
    if stop is not Stop.NONE and stop_price is None:
      raise ValueError('stop_price is required with LOSS or ENTRY')
    params = {
      'type': 'market',
      'client_oid': AuthenticatedClient.make_order_uuid(),
      'side': 'buy' if side == OrderSide.BUY else 'sell',
      'product_id': product_id,
      'stp': self_trade_prevention.value,
    }
    if size is not None:
      params['size'] = size
    if funds is not None:
      params['funds'] = funds
    if stop is not Stop.NONE:
      params['stop'] = stop.value
      params['stop_price'] = stop_price
    response = self._send_post('orders', params=params)
    response['client_oid'] = params['client_oid']
    return response

  def cancel_order(self, order_id, is_client_oid=False, product_id=None):
    """Cancels a single order.

    https://docs.pro.coinbase.com/#cancel-an-order
    """
    params = {}
    if product_id is not None:
      params['product_id'] = product_id
    request_string = 'orders/client:{}' if is_client_oid else 'orders/{}'
    return self._send_delete(request_string.format(order_id), params=params)

  def cancel_all_orders(self, product_id=None):
    """Cancels all orders.

    https://docs.pro.coinbase.com/#cancel-all
    """
    params = {}
    if product_id is not None:
      params['product_id'] = product_id
    return self._send_delete('orders', params=params)

  def list_orders(self, status: list[OrderStatus], product_id=None):
    """Lists Current Open Orders.

    https://docs.pro.coinbase.com/#list-orders
    """
    params = {}
    if product_id is not None:
      params['product_id'] = product_id
    for s in status:
      try:
        params['status'].append(s.value)
      except KeyError:
        params['status'] = [s.value]
    return self._send_paginated_get('orders', params=params)

  def get_order(self, order_id, is_client_oid=False):
    """Gets a single order by ID.

    https://docs.pro.coinbase.com/#get-an-order
    """
    request_string = 'orders/client:{}' if is_client_oid else 'orders/{}'
    return self._send_get(request_string.format(order_id))

  def list_fills(self, order_id=None, product_id=None):
    """List Fills.

    https://docs.pro.coinbase.com/#list-fills
    """
    if order_id is None and product_id is None:
      raise ValueError('order_id or product_id is required')
    params = {}
    if order_id is not None:
      params['order_id'] = order_id
    if product_id is not None:
      params['product_id'] = product_id
    return self._send_paginated_get('fills', params=params)

  def get_current_exchange_limits(self):
    """Gets current exchange limits.

    https://docs.pro.coinbase.com/#get-current-exchange-limits
    """
    return self._send_get('users/self/exchange-limits')

  def list_transfers(self, transfer_type: TransferType, profile_id=None, before=None, after=None, limit=None):
    """List Transfers.

    Deposits: https://docs.pro.coinbase.com/#list-deposits
    Withdrawals: https://docs.pro.coinbase.com/#list-withdrawals
    """
    if limit is not None and limit > 100:
      raise ValueError('cannot request more than 100 transfers')
    params = {
      'type': transfer_type.value
    }
    if limit is not None:
      params['limit'] = limit
    if profile_id is not None:
      params['profile_id'] = profile_id
    if before is not None:
      params['before'] = before
    if after is not None:
      params['after'] = after
    return self._send_get('transfers', params=params)

  def list_deposits(self, **kwargs):
    """List Deposits.

    https://docs.pro.coinbase.com/#list-deposits
    """
    return self.list_transfers(transfer_type=TransferType.DEPOSIT, **kwargs)

  def list_withdrawals(self, **kwargs):
    """List Withdrawals.

    https://docs.pro.coinbase.com/#list-withdrawals
    """
    return self.list_transfers(transfer_type=TransferType.WITHDRAW, **kwargs)

  # There is a Bug in the Coinbase API, so this doesn't work.
  # def get_transfer(self, transfer_id):
  #   return self._send_get('transfers/:{}'.format(transfer_id))

  def get_payment_methods(self):
    """List your Payment Methods.

    https://docs.pro.coinbase.com/#list-payment-methods
    """
    return self._send_get('payment-methods')

  def deposit_funds_payment(self, amount, currency, payment_method_id):
    """Deposit funds from a payment method.

    https://docs.pro.coinbase.com/#payment-method
    """
    params = {
      'amount': amount,
      'currency': currency,
      'payment_method_id': payment_method_id
    }
    return self._send_post('deposits/payment-method', params=params)

  def deposit_funds_coinbase(self, amount, currency, coinbase_account_id):
    """Deposit funds from a Coinbase Account.

    https://docs.pro.coinbase.com/#coinbase
    """
    params = {
      'amount': amount,
      'currency': currency,
      'coinbase_account_id': coinbase_account_id
    }
    return self._send_post('deposits/coinbase-account', params=params)

  def generate_crypto_deposit_address(self, coinbase_account_id):
    """Generate an address for crypto deposits.

    https://docs.pro.coinbase.com/#generate-a-crypto-deposit-address
    """
    return self._send_post('coinbase-accounts/{}/addresses'.format(coinbase_account_id))

  def list_coinbase_accounts(self):
    """Get a list of coinbase accounts.

    https://docs.pro.coinbase.com/#list-payment-methods
    """
    return self._send_get('coinbase-accounts')

  def get_fees(self):
    """Get active fees for your account.

    https://docs.pro.coinbase.com/#fees
    """
    return self._send_get('fees')

  def generate_report(self, report_type: ReportType, start_date, end_date,
                      product_id=None, account_id=None, report_format: ReportFormat = ReportFormat.PDF,
                      email=None):
    """Generates a report.

    https://docs.pro.coinbase.com/#create-a-new-report
    """
    if report_type is ReportType.FILLS and product_id is None:
      raise ValueError('product id is required for ReportType.FILLS')
    if report_type is ReportType.ACCOUNT and account_id is None:
      raise ValueError('account id is required for ReportType.ACCOUNT')
    params = {
      'type': report_type.value,
      'start_date': start_date,
      'end_date': end_date,
      'report_format': report_format.value
    }
    if product_id is not None:
      params['product_id'] = product_id
    if account_id is not None:
      params['account_id'] = account_id
    if email is not None:
      params['email'] = email
    return self._send_post('reports', params=params)

  def get_report_status(self, report_id):
    """Get the status of a report given the id.

    https://docs.pro.coinbase.com/#get-report-status
    """
    return self._send_get('reports/{}'.format(report_id))

  def get_profiles(self, active=False):
    """Get Profiles.

    https://docs.pro.coinbase.com/#list-profiles
    """
    params = {'active': active}
    return self._send_get('profiles', params=params)

  def get_single_profile(self, profile_id):
    """Get a Profile.

    https://docs.pro.coinbase.com/#get-a-profile
    """
    return self._send_get('profiles/{}'.format(profile_id))

  def create_profile_transfer(self, from_profile, to_profile, currency, amount):
    """Creates a transfer from one profile to another.

    https://docs.pro.coinbase.com/#create-profile-transfer
    """
    params = {
      'from': from_profile,
      'to': to_profile,
      'currency': currency,
      'amount': amount
    }
    return self._send_post('profiles/transfer', params=params)

  def get_trailing_volume(self):
    """Gets 30-day trailing volume for all products.

    https://docs.pro.coinbase.com/#trailing-volume
    """
    return self._send_get('users/self/trailing-volume')

  def get_margin_profile_information(self, product_id):
    """Get margin profile information.

    https://docs.pro.coinbase.com/#get-margin-profile-information
    """
    params = {'product_id': product_id}
    return self._send_get('margin/profile_information', params=params)

  def get_buying_power(self, product_id):
    """Get's buying/selling power of particular product.

    https://docs.pro.coinbase.com/#get-buying-power
    """
    params = {'product_id': product_id}
    return self._send_get('margin/buying_power', params=params)

  def get_withdrawl_power(self, currency):
    """Returns the max amount of given currency you can withdraw from your margin profile.

    https://docs.pro.coinbase.com/#get-withdrawal-power
    """
    params = {'currency': currency}
    return self._send_get('margin/withdrawal_power', params=params)

  def get_all_withdrawal_powers(self, currency):
    """Returns max amount of each currency you can withdraw from your margin profile.

    https://docs.pro.coinbase.com/#get-all-withdrawal-powers
    """
    return self._send_get('margin/withdrawal_power_all')

  def get_exit_plan(self):
    """Returns a liquidation strategy to get your equity percentage back to acceptable level.

    https://docs.pro.coinbase.com/#get-exit-plan
    """
    return self._send_get('margin/exit_plan')

  def get_liquidation_history(self):
    """Returns a list of liquidations performed to get your equity percentage about to acceptable level.

    https://docs.pro.coinbase.com/#list-liquidation-history
    """
    return self._send_get('margin/liquidation_history')

  def get_position_refresh_amounts(self):
    """Returns amount in USD of loads that will be renewed in the next day and the day after.

    https://docs.pro.coinbase.com/#get-position-refresh-amounts
    """
    return self._send_get('margin/position_refresh_amounts')

  def get_margin_status(self):
    """Returns margin status.

    https://docs.pro.coinbase.com/#get-margin-status
    """
    return self._send_get('margin/status')

  def get_oracle(self):
    """Get cryptographically signed prices read fo be posted on-chain using Open-Oracle smart contracts.

    https://docs.pro.coinbase.com/#oracle
    """
    return self._send_get('oracle')
