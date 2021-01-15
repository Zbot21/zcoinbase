from enum import Enum, auto


class LogLevel(Enum):
  """Enum for LogLevels in zcoinbase, pick anything from no logging to VERBOSE logging."""
  NO_LOG = 0  # Don't log anything.
  ERROR_LOG = 1  # Only errors logged.
  BASIC_MESSAGES = 2  # Errors logged as well as connection and disconnection.
  VERBOSE_LOG = 3  # Log Everything that might be interesting.

  def __eq__(self, other):
    if self.__class__ is other.__class__:
      return self.value == other.value
    return NotImplemented

  def __gt__(self, other):
    return self.value > other.value

  def __ge__(self, other):
    return self.value >= other.value

  def __lt__(self, other):
    return self.value < other.value

  def __le__(self, other):
    return self.value <= other.value


class OrderSide(Enum):
  BUY = 'buy'
  SELL = 'sell'


class TimeInForce(Enum):
  GOOD_TILL_CANCEL = 'GTC'
  GOOD_UNTIL_TIME = 'GTT'
  IMMEDIATE_OR_CANCEL = 'IOC'
  FILL_OR_KILL = 'FOK'


class Stop(Enum):
  NONE = 'none'
  LOSS = 'loss'
  ENTRY = 'entry'


class SelfTradePrevention(Enum):
  DECREASE_AND_CANCEL = 'dc'
  CANCEL_OLDEST = 'co'
  CANCEL_NEWEST = 'cn'
  CANCEL_BOTH = 'cb'


class OrderStatus(Enum):
  OPEN = 'open'
  PENDING = 'pending'
  ACTIVE = 'active'
  DONE = 'done'


class TransferType(Enum):
  DEPOSIT = 'deposit'
  WITHDRAW = 'withdraw'


class ReportType(Enum):
  FILLS = 'fills'
  ACCOUNT = 'account'


class ReportFormat(Enum):
  PDF = 'pdf'
  CSV = 'csv'
