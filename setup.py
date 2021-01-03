from setuptools import setup

setup(
  name='zcoinbase',
  version='0.0.3',
  packages=['zcoinbase'],
  url='https://github.com/Zbot21/zcoinbase',
  download_url='https://github.com/Zbot21/zcoinbase/archive/v0.0.3.tar.gz',
  license='MIT',
  author='Chris Bellis',
  author_email='chris@zbots.org',
  description='A Simple Coinbase Client for the Coinbase Pro API',
  install_requires=['requests',
                    'websocket-client']

)
