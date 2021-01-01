# zcoinbase

A simple python client that implements simple interfaces to Coinbase Pro.

This project uses minimal libraries to interface with the Coinbase API directly, it does
not depend on any other Coinbase Python libraries (it directly interfaces with the 
REST, Websocket and FIX APIs)

## Warning
This API is in a highly experimental, developmental state, use at your own risk.

## Under Developement
In order of Priorities, here are the TODOs for this.
- Release to PyPi
- REST API
- Simple Client for Dealing with Websocket Messages (Real-time Market)
  - The idea for this is to provide a real-time interface to the market that does not
    require *any* knowledge of how the Websocket API works
- FIX API
