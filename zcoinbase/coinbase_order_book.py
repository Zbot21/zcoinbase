# Maintains a level2 order book of Coinbase
import uuid

from operator import neg
from sortedcontainers import SortedDict
from threading import Lock
from typing import Text, Callable

from zcoinbase import CoinbaseWebsocket


class ProductOrderBook:
  def __init__(self, product_id):
    self.product_id = product_id
    self._asks = SortedDict(lambda key: float(key))
    self._asks_lock = Lock()
    self._bids = SortedDict(lambda key: neg(float(key)))
    self._bids_lock = Lock()
    self._first_bids_lock = Lock()
    self._first_bids_lock.acquire()
    self._first_asks_lock = Lock()
    self._first_asks_lock.acquire()
    self._update_callbacks = {}

  def add_update_callback(self, callback: Callable):
    """Add a callback to be called on every update. The callback will be called with 'self' as a parameter.

    Returns:
      A unique identifier (str) that can be used to remove the callback in the future.
    """
    identifier = str(uuid.uuid4())
    self._update_callbacks[identifier] = callback
    return identifier

  def remove_update_callback(self, identifier: Text):
    """Removes the callback by it's identifier."""
    del self._update_callbacks[identifier]

  def top_n_string(self, n=None):
    """Returns the "Top-N" asks/bids in the order-book in string form.

    Params:
      n: How many of the top
    """
    with self._bids_lock and self._asks_lock:
      return ProductOrderBook._make_formatted_string(
        bids=ProductOrderBook._make_sorted_dict_slice(self._bids, stop=n),
        asks=ProductOrderBook._make_sorted_dict_slice(self._asks, stop=n)
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
    with self._asks_lock:
      return ProductOrderBook._make_slice(self._asks, stop=top_n)

  def get_bids(self, top_n=None):
    """Get the 'bids' part of the order book.

        Params:
          top_n: The depth of the order book to return.
        """
    with self._bids_lock:
      return ProductOrderBook._make_slice(self._bids, stop=top_n)

  # Private API Below this Line.
  def _call_callbacks(self):
    for callback in self._update_callbacks.values():
      callback(self)

  def _init_bids(self, bids):
    with self._bids_lock:
      self._bids.clear()  # init should clear all current bids.
      for price, size in bids:
        self._bids[price] = float(size)
      self._first_bids_lock.release()
    self._call_callbacks()

  def _init_asks(self, asks):
    with self._asks_lock:
      self._asks.clear()  # init should clear all current asks.
      for price, size in asks:
        self._asks[price] = float(size)
      self._first_asks_lock.release()
    self._call_callbacks()

  def _consume_changes(self, changes):
    for side, price, size in changes:
      if side == 'buy':
        self._consume_buy(price, size)
      elif side == 'sell':
        self._consume_sell(price, size)
    self._call_callbacks()

  def _consume_buy(self, price, size):
    fsize = float(size)
    # Wait for _init_bids to run.
    if self._first_bids_lock.locked():
      self._first_bids_lock.acquire()
      self._first_bids_lock.release()
    with self._bids_lock:
      if str(fsize) == '0.0':
        del self._bids[price]
      else:
        self._bids[price] = fsize

  def _consume_sell(self, price, size):
    fsize = float(size)
    # Wait for _init_asks to run.
    if self._first_asks_lock.locked():
      self._first_asks_lock.acquire()
      self._first_asks_lock.release()
    with self._asks_lock:
      if str(fsize) == '0.0':
        del self._asks[price]
      else:
        self._asks[price] = fsize

  @staticmethod
  def _make_formatted_string(bids, asks):
    overall_format = "BIDS:\n{}\n\nASKS:\n{}\n\n"
    format_str = 'PRICE: {}, SIZE: {}'
    return overall_format.format(
      '\n'.join(format_str.format(str(price), str(bids[price])) for price in bids.keys()),
      '\n'.join(format_str.format(str(price), str(asks[price])) for price in asks.keys()))

  def __repr__(self):
    """Print the entire order book."""
    with self._asks_lock and self._bids_lock:
      return ProductOrderBook._make_formatted_string(self._bids, self._asks)

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
    self._order_books = {}
    for product in self.coinbase_websocket.products_to_listen:
      self._order_books[product] = ProductOrderBook(product)
    self.coinbase_websocket.add_channel_function('l2update',
                                                 lambda message: self._update_order_book(message['product_id'],
                                                                                         message['changes']),
                                                 refresh_subscriptions=False)
    self.coinbase_websocket.add_channel_function('snapshot',
                                                 lambda message: self._initial_snapshot(message['product_id'],
                                                                                        bids=message['bids'],
                                                                                        asks=message['asks']),
                                                 refresh_subscriptions=False)

  @classmethod
  def make_order_book(cls, product_ids: list[Text], websocket_addr=CoinbaseWebsocket.PROD_ADDRESS):
    """Make an order-book with it's own websocket and starts that websocket."""
    coinbase_websocket = CoinbaseWebsocket(websocket_addr=websocket_addr,
                                           products_to_listen=product_ids,
                                           autostart=False)
    order_book = cls(coinbase_websocket)
    coinbase_websocket.start_websocket_in_thread()
    coinbase_websocket.wait_for_open()
    return order_book

  def get_order_book(self, product_id) -> ProductOrderBook:
    if product_id in self._order_books:
      return self._order_books[product_id]
    else:
      raise ValueError('Don\'t have order book for {}'.format(product_id))

  def get_tracked_products(self):
    return self._order_books.keys()

  def add_order_books(self, product_ids: list[Text], refresh_subscriptions=True):
    for product_id in product_ids:
      if product_id not in self._order_books:
        self._order_books[product_id] = ProductOrderBook(product_id)
        self.coinbase_websocket.add_product(product_id, refresh_subscriptions=False)
    if refresh_subscriptions:
      self.coinbase_websocket.subscribe()

  def add_callback(self, product_id: Text, callback: Callable[[ProductOrderBook], None]):
    if product_id in self._order_books:
      return self._order_books[product_id].add_update_callback(callback)
    else:
      raise ValueError('Don\'t have order book for {}'.format(product_id))

  def _initial_snapshot(self, product_id, bids, asks):
    if product_id in self._order_books:
      self._order_books[product_id]._init_bids(bids)
      self._order_books[product_id]._init_asks(asks)

  def _update_order_book(self, product_id, changes):
    if product_id in self._order_books:
      self._order_books[product_id]._consume_changes(changes)
