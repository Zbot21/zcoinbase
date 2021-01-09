import csv
import datetime
import math
import sys

from dateutil import parser
from functools import partial
from typing import Text
from zcoinbase import PublicClient
from zcoinbase.internal import RateLimitedExecutionQueue

# Magically use absl logging if available.
import importlib

absl_spec = importlib.util.find_spec('absl')
if absl_spec is not None:
  # Use absl logging if it's available on the environment.
  from absl import logging
  logging.set_verbosity(logging.INFO)
else:
  # Use python default logging if it is not available.
  import logging

# Import progressbar if available.
progressbar_spec = importlib.util.find_spec('progressbar')
if progressbar_spec is not None:
  import progressbar


class HistoricalDownloader:
  TIMESLICE_MAPPINGS = {
    '1m': '60',
    '5m': '300',
    '15m': '900',
    '1h': '3600',
    '6h': '21600',
    '1d': '86400'
  }

  TIMESLICE_MUST_BE_ONE_OF_STRING = ", ".join(
    list(TIMESLICE_MAPPINGS.keys()) + list(TIMESLICE_MAPPINGS.values()))

  _MAX_CANDLES = 300

  def __init__(self, product_id: Text, start_time, end_time, granularity: Text, output_filename: Text,
               rest_url=PublicClient.PROD_URL, enable_progressbar=True):
    self.public_client = PublicClient(rest_url=rest_url)
    self.product_id = product_id
    self.output_filename = output_filename
    self.enable_progressbar = enable_progressbar
    if isinstance(start_time, str):
      self.start_time = parser.parse(start_time)
    elif isinstance(start_time, datetime.datetime):
      self.start_time = start_time
    else:
      raise ValueError('start_time must be either string or datetime.datetime.')
    if isinstance(end_time, str):
      self.end_time = parser.parse(end_time)
    elif isinstance(end_time, datetime.datetime):
      self.end_time = end_time
    else:
      raise ValueError('end_time must be either string or datetime.datetime')
    if start_time > end_time:
      raise ValueError('start_time must be before end_time')
    if not HistoricalDownloader.validate_granularity(granularity):
      raise ValueError('Granularity must be one of [{}]'.format(HistoricalDownloader.TIMESLICE_MUST_BE_ONE_OF_STRING))
    if granularity in HistoricalDownloader.TIMESLICE_MAPPINGS:
      self.granularity = int(HistoricalDownloader.TIMESLICE_MAPPINGS[granularity])
    else:
      self.granularity = int(granularity)

  def _make_interval_call(self, product_id: Text, start_time: datetime.datetime, end_time: datetime.datetime,
                          granularity):
    return self.public_client.get_historic_rates(product_id, start=start_time.isoformat(), end=end_time.isoformat(),
                                                 granularity=granularity)

  def download_and_write_to_file(self):
    # First determine the number of candles that would be returned at the desired granularity.
    required_calls = HistoricalDownloader._solve_required_calls(start_time=self.start_time, end_time=self.end_time,
                                                                granularity=self.granularity)
    logging.info('Making {} calls to Coinbase API.'.format(len(required_calls)))
    with RateLimitedExecutionQueue(max_calls_per_interval=3, interval=1) as queue:
      results = []
      for start_time, end_time in required_calls:
        logging.debug('Call with Start Time: {} and End Time: {}'.format(start_time, end_time))
        results.append(queue.add_function_to_pool(
          partial(self._make_interval_call, self.product_id, start_time, end_time, self.granularity)))
      bar = None
      bar_progress = 0
      if self.enable_progressbar and 'progressbar' in sys.modules:
        bar = progressbar.ProgressBar(maxval=len(results),
                                      widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage(), ' [',
                                               progressbar.ETA(), '] '])
        bar.start()
      with open(self.output_filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write the header.
        csv_writer.writerow(['time', 'low', 'high', 'open', 'close', 'volume'])
        for result in results:
          actual_result = sorted(result.get(), key=lambda x: x[0])
          logging.debug('Actual Returned Result: {}'.format(actual_result))
          if bar:
            bar_progress += 1
            bar.update(bar_progress)
          for row in actual_result:
            # Convert the time to an ISO timestamp.
            write_row = row[1:]
            write_row.insert(0, datetime.datetime.utcfromtimestamp(row[0]).isoformat())
            csv_writer.writerow(write_row)
      if bar:
        bar.finish()

  @staticmethod
  def _solve_required_calls(start_time: datetime.datetime, end_time: datetime.datetime, granularity: int):
    """Solves the calls that are required to get all date between start_time and end_time with the given granularity.

    Returns:
      A list of tuples representing the start and end times required to get all data between start_time and end_time.
    """
    total_interval = end_time - start_time
    # First solve the max delta for the interval (this is the largest delta we can use)
    max_delta = datetime.timedelta(seconds=HistoricalDownloader._MAX_CANDLES * granularity)
    # Special case, we can just make a single call and we will be under the maximum amount that can
    # be returned by the API.
    if total_interval < max_delta:
      return [(start_time, end_time)]
    required_calls = []
    current_time = start_time
    num_required_calls = math.floor(total_interval / max_delta)
    for _ in range(num_required_calls):
      new_end_time = current_time + max_delta
      required_calls.append((current_time, new_end_time))
      current_time = new_end_time
    # The last interval goes to the end time.
    required_calls.append((current_time, end_time))
    return required_calls

  @staticmethod
  def validate_granularity(granularity: Text):
    return granularity in list(HistoricalDownloader.TIMESLICE_MAPPINGS.keys()) + list(
      HistoricalDownloader.TIMESLICE_MAPPINGS.values())
