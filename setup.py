from setuptools import setup, find_packages

VERSION_NUMBER = '0.0.8'

setup(
  name='zcoinbase',
  version=VERSION_NUMBER,
  packages=find_packages(),
  url='https://github.com/Zbot21/zcoinbase',
  download_url='https://github.com/Zbot21/zcoinbase/archive/v{}.tar.gz'.format(VERSION_NUMBER),
  license='MIT',
  author='Chris Bellis',
  author_email='chris@zbots.org',
  description='A Simple Coinbase Client for the Coinbase Pro API',
  install_requires=['requests',
                    'websocket-client',
                    'sortedcontainers',
                    'python-dateutil',
                    'pandas']
)
