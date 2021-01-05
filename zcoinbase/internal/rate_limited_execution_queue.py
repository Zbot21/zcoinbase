from contextlib import AbstractContextManager
from functools import partial
from multiprocessing.pool import ThreadPool
from threading import BoundedSemaphore, Thread, Event
from typing import Callable, Any


class RateLimitedExecutionQueue(AbstractContextManager):
  def __init__(self, max_calls_per_interval: int, interval: float = 1):
    self.max_calls_per_interval = max_calls_per_interval
    self.interval = interval
    self._call_limiter = BoundedSemaphore(self.max_calls_per_interval)
    self._exit = Event()
    self._refresher_thread = Thread(target=self._refresh_semaphore,
                                    daemon=True)
    self._refresher_thread.start()
    self._execution_pool = ThreadPool(processes=1)

  def close_and_join(self):
    """Close the execution pool and wait for all functions to complete."""
    self._execution_pool.close()
    self._execution_pool.join()
    self._exit.set()
    self._refresher_thread.join()

  def __exit__(self, *args):
    self.close_and_join()

  @staticmethod
  def _function_wrapper(limiter: BoundedSemaphore, function: Callable[[], None]):
    limiter.acquire()
    return function()

  def add_function_to_pool(self, function: Callable[[], Any]):
    return self._execution_pool.apply_async(
      partial(RateLimitedExecutionQueue._function_wrapper, self._call_limiter, function))

  def _refresh_semaphore(self):
    while not self._exit.is_set():
      try:
        # Try to release 3 semaphores.
        for _ in range(self.max_calls_per_interval):
          self._call_limiter.release()
      except Exception:
        pass
      finally:
        pass  # We expect this exception.
      self._exit.wait(timeout=self.interval)


def function_to_call(num_to_print):
  print('NUM: {}'.format(num_to_print))


def second_function_to_call(num_to_print):
  print('NUM2: {}'.format(num_to_print))


if __name__ == '__main__':
  queue = RateLimitedExecutionQueue(1, 3)
  for i in range(10):
    queue.add_function_to_pool(partial(function_to_call, i))
  queue.close_and_join()
