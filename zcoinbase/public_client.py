from .rest_client import RestClient


class PublicClient(RestClient):
  """zcoinbase public client API.

  Public API Documentation:
    https://docs.pro.coinbase.com/#market-data

  Attributes:
    rest_url: REST API URL. Defaults to https://api.pro.coinbase.com
  """

  _SANDBOX_URL = 'https://api-public.sandbox.pro.coinbase.com'
  _PROD_URL = 'https://api.pro.coinbase.com'

  def __init__(self, rest_url=_PROD_URL):
    super().__init__(rest_url)

  @classmethod
  def make_prod_client(cls):
    return cls(rest_url=cls._PROD_URL)

  @classmethod
  def make_sandbox_client(cls):
    return cls(rest_url=cls._SANDBOX_URL)

  def get_products(self):
    return self._send_get('products')

  def get_product(self, product_id):
    return self._send_get('products/{}'.format(product_id))

  def get_order_book(self, product_id, level=1):
    if 1 <= level >= 3:
      raise ValueError('Level must be between 1 and three.')
    params = {'level': level}
    return self._send_get('products/{}/book'.format(product_id), params=params)

  def get_ticker(self, product_id):
    return self._send_get('products/{}/ticker'.format(product_id))

  def get_trades(self, product_id):
    return self._send_paginated_get('products/{}/trades')

  def get_historic_rates(self, product_id, start=None, end=None, granularity=None):
    params = dict()
    accepted_granularities = {60, 300, 900, 3600, 21600, 86400}
    if granularity is not None:
      if granularity not in accepted_granularities:
        raise ValueError(
          'Specified Granularity is {}, must be in approved values: {}'.format(granularity, accepted_granularities))
      params['granularity'] = granularity
    if start is not None:
      params['start'] = start
    if end is not None:
      params['end'] = end
    return self._send_get('products/{}/candles'.format(product_id), params=params)

  def get_24hr_stats(self, product_id):
    return self._send_get('products/{}/stats'.format(product_id))

  def get_currencies(self):
    return self._send_get('currencies')

  def get_currency(self, currency_id):
    return self._send_get('currencies/{}'.format(currency_id))

  def get_time(self):
    return self._send_get('time')
