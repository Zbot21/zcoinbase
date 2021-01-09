import csv
import datetime
import math
import sys
import pandas as pd

from dateutil import parser
from functools import partial
from typing import Text, Callable
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

  _COLUMN_HEADERS = ['time', 'low', 'high', 'open', 'close', 'volume']

  def __init__(self, product_id: Text, start_time, end_time, granularity: Text,
               rest_url=PublicClient.PROD_URL, enable_progressbar=True):
    self.public_client = PublicClient(rest_url=rest_url)
    self.product_id = product_id
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

  def _download_with_queue(self, row_function: Callable[[list[Text]], None], queue: RateLimitedExecutionQueue):
    """A _download method that allows you to set your own RateLimitedExecutionQueue, might be useful in larger API."""
    # First find the required number of calls at the given granularity, and the start/end times that should be used.
    required_calls = HistoricalDownloader._solve_required_calls(start_time=self.start_time, end_time=self.end_time,
                                                                granularity=self.granularity)
    # Create a time-estimate.
    estimated_time = datetime.timedelta(seconds=(len(required_calls) / queue.max_calls_per_interval) * queue.interval)
    logging.info(
      'Making {} calls to Coinbase API. This will take approximately: {}'.format(len(required_calls), estimated_time))
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
    for result in results:
      actual_result = sorted(result.get(), key=lambda x: x[0])
      logging.debug('Actual Returned Result: {}'.format(actual_result))
      if bar:
        bar_progress += 1
        bar.update(bar_progress)
      for row in actual_result:
        row_function(row)
    if bar:
      bar.finish()

  def _download(self, row_function: Callable[[list], None]):
    """Downloads historical data and calls the row_function with the text of each row."""
    # Set up RateLimitedExecutionQueue with max_calls_per_interval set to 3 and the interval set to 1 second.
    # This matches with the limits configured for coinbase itself.
    with RateLimitedExecutionQueue(max_calls_per_interval=3, interval=1) as queue:
      self._download_with_queue(row_function, queue)

  @staticmethod
  def _write_row_to_csv(csv_writer, row: list):
    # Convert the time to an ISO timestamp.
    write_row = row[1:]
    write_row.insert(0, datetime.datetime.utcfromtimestamp(row[0]).isoformat())
    csv_writer.writerow(write_row)

  def download_and_write_to_file(self, output_filename: Text):
    """Downloads historical data and writes it to a file."""
    with open(output_filename, 'w', newline='') as csv_file:
      csv_writer = csv.writer(csv_file)
      csv_writer.writerow(HistoricalDownloader._COLUMN_HEADERS)
      self._download(partial(HistoricalDownloader._write_row_to_csv, csv_writer))

  @staticmethod
  def _write_row_to_dataframe(df: pd.DataFrame, row: list):
    timestamp = pd.Timestamp(datetime.datetime.utcfromtimestamp(row[0]).isoformat())
    logging.debug('writing {} to {}'.format(timestamp, row))
    df.loc[timestamp] = row

  def download_to_dataframe(self):
    """Downloads the historical data specified by this class to a dataframe."""
    df = pd.DataFrame(columns=HistoricalDownloader._COLUMN_HEADERS)
    self._download(partial(HistoricalDownloader._write_row_to_dataframe, df))
    df.set_index('time')
    return df

  def download_to_list(self):
    """Downloads the historical data in the form of a list, like it would be returned by Coinbase."""
    output = list()
    self._download(output.append)
    return output

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
