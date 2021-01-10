# zcoinbase

A simple python client that implements simple interfaces to Coinbase Pro API.

This project uses minimal libraries to interface with the Coinbase API directly, it does
not depend on any other Coinbase Python libraries (it directly interfaces with the 
REST, Websocket and FIX APIs)

## Coinbase API
If you plan on using this API, you should familiarize yourself with the Coinbase Pro API here: https://docs.pro.coinbase.com/ 

## Using

zcoibase is hosted on PyPI, so the easiest way to get started is to run:
`pip install zcoinbase`

## Notable Features
* Easy-to-use, function-based Websocket client with support for functional programming of websocket messages.
* Features a Websocket-based real-time Order-book on the websocket API.
* Historical Data Downloader, should make it easy to download historical data from the markets.

### Examples
Examples on how to use zcoinbase can be found in the `examples` directory.

## Warning
This API is in a highly experimental, developmental state, use at your own risk.

## Under Developement
In order of Priorities, here are the TODOs for this.
- Simple Client for Dealing with Websocket Messages (Real-time Market)
  - The idea for this is to provide a real-time interface to the market that does not
    require *any* knowledge of how the Websocket API works
- FIX API
