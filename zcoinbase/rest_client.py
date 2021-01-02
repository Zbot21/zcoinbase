import requests
import json


class RestClient:
  def __init__(self, rest_url='https://api.pro.coinbase.com'):
    self.rest_url = rest_url.rstrip('/')
    self.session = requests.sessions.Session()
    self.auth = None

  def _send_get(self, endpoint, params=None):
    return RestClient._append_status_code(
      self.session.get('{}/{}'.format(self.rest_url, endpoint), params=params, auth=self.auth))

  def _send_paginated_get(self, endpoint, params=None):
    if params is None:
      params = dict()
    url = '{}/{}'.format(self.rest_url, endpoint)
    while True:
      r = self.session.get(url, params=params, auth=self.auth, timeout=30)
      results = r.json()
      for result in results:
        yield result
      if not r.headers.get('cb-after') or params.get('before') is not None:
        break
      else:
        params['after'] = r.headers['cb-after']

  def _send_post(self, endpoint, params=None, data=None):
    return RestClient._append_status_code(
      self.session.post('{}/{}'.format(self.rest_url, endpoint),
                        data=json.dumps(params) if params is not None else None, auth=self.auth))

  def _send_delete(self, endpoint, params=None):
    return RestClient._append_status_code(
      self.session.delete('{}/{}'.format(self.rest_url, endpoint), params=params, auth=self.auth))

  @staticmethod
  def _append_status_code(response):
    response_json = response.json()
    response_json['http_code'] = response.status_code
    return response_json
