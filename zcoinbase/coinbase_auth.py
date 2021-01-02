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
  def get_auth_headers(timestamp, message, api_key, api_secret, passphrase):
    message = message.encode('ascii')
    hmac_key = base64.b64decode(api_secret)
    signature = hmac.new(hmac_key, message, hashlib.sha256)
    signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
    return {
      'Content-Type': 'Application/JSON',
      'CB-ACCESS-SIGN': signature_b64,
      'CB-ACCESS-TIMESTAMP': timestamp,
      'CB-ACCESS-KEY': api_key,
      'CB-ACCESS-PASSPHRASE': passphrase
    }
