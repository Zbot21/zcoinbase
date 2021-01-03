import hmac
import hashlib
import time
import base64

from requests.auth import AuthBase


class CoinbaseAuth(AuthBase):
  """Coinbase Auth.

  API Information: https://docs.pro.coinbase.com/#signing-a-message
  """

  def __init__(self, api_key, api_secret, passphrase,
               time_provider=lambda: time.time()):
    self.api_key = api_key
    self.api_secret = api_secret
    self.passphrase = passphrase
    self.time_provider = time_provider

  def __call__(self, request):
    timestamp = str(self.time_provider())
    message = ''.join([timestamp, request.method, request.path_url, (request.body or '')])
    request.headers.update(
      CoinbaseAuth.get_auth_headers(timestamp, message, self.api_key, self.api_secret, self.passphrase))
    return request

  @staticmethod
  def get_websocket_verification(api_key, api_secret, passphrase):
    timestamp = str(time.time())
    message = ''.join([timestamp, 'GET', '/users/self/verify'])
    auth = CoinbaseAuth.make_auth(timestamp, message, api_key, api_secret, passphrase)
    return {
      'signature': auth[0],
      'timestamp': auth[1],
      'key': auth[2],
      'passphrase': auth[3]
    }

  @staticmethod
  def get_auth_headers(timestamp, message, api_key, api_secret, passphrase):
    auth = CoinbaseAuth.make_auth(timestamp, message, api_key, api_secret, passphrase)
    return {
      'Content-Type': 'Application/JSON',
      'CB-ACCESS-SIGN': auth[0],
      'CB-ACCESS-TIMESTAMP': auth[1],
      'CB-ACCESS-KEY': auth[2],
      'CB-ACCESS-PASSPHRASE': auth[3]
    }

  @staticmethod
  def make_auth(timestamp, message, api_key, api_secret, passphrase):
    message = message.encode('ascii')
    hmac_key = base64.b64decode(api_secret)
    signature = hmac.new(hmac_key, message, hashlib.sha256)
    signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
    return signature_b64, timestamp, api_key, passphrase

