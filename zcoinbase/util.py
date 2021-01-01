from enum import Enum


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
    if self.__class__ is other.__class__:
      return self.value > other.value
    return NotImplemented

  def __ge__(self, other):
    if self.__class__ is other.__class__:
      return self.value >= other.value
    return NotImplemented
