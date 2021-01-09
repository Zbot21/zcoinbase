import datetime

from absl import app, flags, logging
from dateutil import parser
from typing import Text
from zcoinbase import HistoricalDownloader, PublicClient

FLAGS = flags.FLAGS
flags.DEFINE_string('rest_url', PublicClient.PROD_URL, 'The URL of the Coinbase client to read from.')
flags.DEFINE_string('product_id', 'BTC-USD', 'The product to download data for.')
flags.DEFINE_string('start_time', None, 'The time to start at. Parsed by dateutil.parser.parse.')
flags.DEFINE_string('end_time', None, 'The time to end at. Parsed by dateutil.parser.parse')
flags.DEFINE_string('granularity', None,
                    'The granularity to download data at, must be one of [{}]'.format(
                      HistoricalDownloader.TIMESLICE_MUST_BE_ONE_OF_STRING))
flags.DEFINE_string('output_file', None, 'The file to output csv data to.')
flags.mark_flag_as_required('output_file')


def validate_time_parsable(time_string: Text):
  try:
    parser.parse(time_string)
  except ValueError as e:
    logging.error('Could not parse {}, {}'.format(time_string, e))
    return False
  return True


flags.mark_flags_as_required(['start_time', 'end_time'])
flags.register_validator('start_time', validate_time_parsable, message='--start_time must be parsable by dateutil.')
flags.register_validator('end_time', validate_time_parsable, message='--end_time must be parsable by dateutil.')


@flags.multi_flags_validator(['start_time', 'end_time'],
                             message='start_time must be before end_time')
def validate_start_time_before_end_time(flags_dict):
  return parser.parse(flags_dict['start_time']) < parser.parse(flags_dict['end_time'])


flags.mark_flag_as_required('granularity')
flags.register_validator('granularity', HistoricalDownloader.validate_granularity,
                         message='--granularity must be one of [{}]'.format(
                           HistoricalDownloader.TIMESLICE_MUST_BE_ONE_OF_STRING))


def main(argv):
  historical_downloader = HistoricalDownloader(
    product_id=FLAGS.product_id,
    rest_url=FLAGS.rest_url,
    start_time=FLAGS.start_time,
    end_time=FLAGS.end_time,
    granularity=FLAGS.granularity,
    output_filename=FLAGS.output_file
  )
  historical_downloader.download_and_write_to_file()


if __name__ == '__main__':
  app.run(main)
