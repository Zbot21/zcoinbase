# Maintains a level2 order book of Coinbase

from operator import neg
from sortedcontainers import SortedDict
from threading import Lock
from typing import Text

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
    """Returns the "Top-N" asks/bids in the order-book in string form.

    Params:
      n: How many of the top
    """
    with self.bids_lock and self.asks_lock:
      return ProductOrderBook._make_formatted_string(
        bids=ProductOrderBook._make_sorted_dict_slice(self.bids, stop=n),
        asks=ProductOrderBook._make_sorted_dict_slice(self.asks, stop=n)
      )

  def get_book(self, top_n=None):
    """Returns the order book as a dict with keys 'asks' and 'bids' and tuples of [price, size].

    Params:
      top_n: The depth of the order book to return.
    """
    return {
      'asks': self.get_asks(top_n=top_n),
      'bids': self.get_bids(top_n=top_n)
    }

  def get_asks(self, top_n=None):
    """Get the 'asks' part of the order book.

    Params:
      top_n: The depth of the order book to return.
    """
    with self.asks_lock:
      return ProductOrderBook._make_slice(self.asks, stop=top_n)

  def get_bids(self, top_n=None):
    """Get the 'bids' part of the order book.

        Params:
          top_n: The depth of the order book to return.
        """
    with self.bids_lock:
      bids_slice = ProductOrderBook._make_slice(self.bids, stop=top_n)

  # Private API Below this Line.
  def _init_bids(self, bids):
    with self.bids_lock:
      for price, size in bids:
        self.bids[price] = float(size)
      self.first_bids_lock.release()

  def _init_asks(self, asks):
    with self.asks_lock:
      for price, size in asks:
        self.asks[price] = float(size)
      self.first_asks_lock.release()

  def _consume_changes(self, changes):
    for side, price, size in changes:
      if side == 'buy':
        self._consume_buy(price, size)
      elif side == 'sell':
        self._consume_sell(price, size)

  def _consume_buy(self, price, size):
    fsize = float(size)
    # Wait for _init_bids to run.
    if self.first_bids_lock.locked():
      self.first_bids_lock.acquire()
      self.first_bids_lock.release()
    with self.bids_lock:
      if str(fsize) == '0.0':
        del self.bids[price]
      else:
        self.bids[price] = fsize

  def _consume_sell(self, price, size):
    fsize = float(size)
    # Wait for _init_asks to run.
    if self.first_asks_lock.locked():
      self.first_asks_lock.acquire()
      self.first_asks_lock.release()
    with self.asks_lock:
      if str(fsize) == '0.0':
        del self.asks[price]
      else:
        self.asks[price] = fsize

  @staticmethod
  def _make_formatted_string(bids, asks):
    overall_format = "BIDS:\n{}\n\nASKS:\n{}\n\n"
    format_str = 'PRICE: {}, SIZE: {}'
    return overall_format.format(
      '\n'.join(format_str.format(str(price), str(bids[price])) for price in bids.keys()),
      '\n'.join(format_str.format(str(price), str(asks[price])) for price in asks.keys()))

  def __repr__(self):
    """Print the entire order book."""
    with self.asks_lock and self.bids_lock:
      return ProductOrderBook._make_formatted_string(self.bids, self.asks)

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

  def get_tracked_products(self):
    return self.order_books.keys()

  def add_order_books(self, product_ids: list[Text], refresh_subscriptions=True):
    for product_id in product_ids:
      if product_id not in self.order_books:
        self.order_books[product_id] = ProductOrderBook(product_id)
        self.coinbase_websocket.add_product(product_id, refresh_subscriptions=False)
    if refresh_subscriptions:
      self.coinbase_websocket.subscribe()

  def initial_snapshot(self, product_id, bids, asks):
    if product_id in self.order_books:
      self.order_books[product_id]._init_bids(bids)
      self.order_books[product_id]._init_asks(asks)

  def update_order_book(self, product_id, changes):
    if product_id in self.order_books:
      self.order_books[product_id]._consume_changes(changes)
