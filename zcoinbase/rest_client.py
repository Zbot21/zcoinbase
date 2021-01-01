import requests


class RestClient:
  def __init__(self, rest_url='https://api.pro.coinbase.com'):
    self.rest_url = rest_url.rstrip('/')
    self.session = requests.sessions.Session()

  def _send_get(self, endpoint, params=None):
    return self.session.get('{}/{}'.format(self.rest_url, endpoint), params=params).json()

  def _send_paginated_get(self, endpoint, params=None):
    if params is None:
      params = dict()
    url = '{}/{}'.format(self.rest_url, endpoint)
    while True:
      r = self.session.get(url, params=params)
      results = r.json()
      for result in results:
        yield result
      if not r.headers.get('cb-after') or params.get('before') is not None:
        break
      else:
        params['after'] = r.headers['cb-after']
