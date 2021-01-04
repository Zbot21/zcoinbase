# Maintains a level2 order book of Coinbase

from operator import neg
from sortedcontainers import SortedDict
from threading import Lock

from zcoinbase import CoinbaseWebsocket


class ProductOrderBook:
  def __init__(self, product_id):
    self.product_id = product_id
    self.asks = SortedDict(lambda key: float(key))
    self.asks_lock = Lock()
    self.bids = SortedDict(lambda key: neg(float(key)))
    self.bids_lock = Lock()
    self.first_bids_lock = Lock()
    self.first_bids_lock.acquire()
    self.first_asks_lock = Lock()
    self.first_asks_lock.acquire()

  def top_n_string(self, n=None):
    """Returns the "Top-N" asks/bids in the order-book.


    """
    self.bids_lock.acquire()
    self.asks_lock.acquire()
    formatted_string = ProductOrderBook._make_formatted_string(
      bids=ProductOrderBook._make_sorted_dict_slice(self.bids, stop=n),
      asks=ProductOrderBook._make_sorted_dict_slice(self.asks, stop=n)
    )
    self.bids_lock.release()
    self.asks_lock.release()
    return formatted_string

  def get_book(self, top_n=None):
    return {
      'asks': self.get_asks(top_n=top_n),
      'bids': self.get_bids(top_n=top_n)
    }

  def get_asks(self, top_n=None):
    self.asks_lock.acquire()
    asks_slice = ProductOrderBook._make_slice(self.asks, stop=top_n)
    self.asks_lock.release()
    return asks_slice

  def get_bids(self, top_n=None):
    self.bids_lock.acquire()
    bids_slice = ProductOrderBook._make_slice(self.bids, stop=top_n)
    self.bids_lock.release()
    return bids_slice

  # Private API Below this Line.
  def _init_bids(self, bids):
    self.bids_lock.acquire()
    for price, size in bids:
      self.bids[price] = float(size)
    self.bids_lock.release()
    self.first_bids_lock.release()

  def _init_asks(self, asks):
    self.asks_lock.acquire()
    for price, size in asks:
      self.asks[price] = float(size)
    self.asks_lock.release()
    self.first_asks_lock.release()

  def _consume_changes(self, changes):
    for side, price, size in changes:
      if side == 'buy':
        self._consume_buy(price, size)
      elif side == 'sell':
        self._consume_sell(price, size)

  def _consume_buy(self, price, size):
    fsize = float(size)
    if self.first_bids_lock.locked():
      self.first_bids_lock.acquire()
      self.first_bids_lock.release()
    self.bids_lock.acquire()
    if str(fsize) == '0.0':
      del self.bids[price]
    else:
      self.bids[price] = fsize
    self.bids_lock.release()

  def _consume_sell(self, price, size):
    fsize = float(size)
    if self.first_asks_lock.locked():
      self.first_asks_lock.acquire()
      self.first_asks_lock.release()
    self.asks_lock.acquire()
    if str(fsize) == '0.0':
      del self.asks[price]
    else:
      self.asks[price] = fsize
    self.asks_lock.release()

  @staticmethod
  def _make_formatted_string(bids, asks):
    overall_format = "BIDS:\n{}\n\nASKS:\n{}\n\n"
    format_str = 'PRICE: {}, SIZE: {}'
    return overall_format.format(
      '\n'.join(format_str.format(str(price), str(bids[price])) for price in bids.keys()),
      '\n'.join(format_str.format(str(price), str(asks[price])) for price in asks.keys()))

  def __repr__(self):
    self.bids_lock.acquire()
    self.asks_lock.acquire()
    formatted_string = ProductOrderBook._make_formatted_string(self.bids, self.asks)
    self.bids_lock.release()
    self.asks_lock.release()
    return formatted_string

  @staticmethod
  def _make_sorted_dict_slice(orders: SortedDict, start=None, stop=None):
    return SortedDict(orders.key, [(key, orders[key]) for key in orders.islice(start=start, stop=stop)])

  @staticmethod
  def _make_slice(orders: SortedDict, start=None, stop=None):
    return [(key, orders[key]) for key in orders.islice(start=start, stop=stop)]


class CoinbaseOrderBook:
  def __init__(self, cb_ws: CoinbaseWebsocket):
    self.coinbase_websocket = cb_ws
    self.coinbase_websocket.add_channel('level2')
    self.order_books = {}
    for product in self.coinbase_websocket.products_to_listen:
      self.order_books[product] = ProductOrderBook(product)
    self.coinbase_websocket.add_channel_function('l2update',
                                                 lambda message: self.update_order_book(message['product_id'],
                                                                                        message['changes']),
                                                 refresh_subscriptions=False)
    self.coinbase_websocket.add_channel_function('snapshot',
                                                 lambda message: self.initial_snapshot(message['product_id'],
                                                                                       bids=message['bids'],
                                                                                       asks=message['asks']),
                                                 refresh_subscriptions=False)

  def get_order_book(self, product_id) -> ProductOrderBook:
    if product_id in self.order_books:
      return self.order_books[product_id]
    else:
      raise ValueError('Don\'t have order book for {}'.format(product_id))

  def initial_snapshot(self, product_id, bids, asks):
    if product_id in self.order_books:
      self.order_books[product_id]._init_bids(bids)
      self.order_books[product_id]._init_asks(asks)

  def update_order_book(self, product_id, changes):
    if product_id in self.order_books:
      self.order_books[product_id]._consume_changes(changes)