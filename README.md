# PJON-python
Pythonic interface to PJON communication protocol.

Current status: 
- work in progress
- initially PHY abstraction provided by a serial-PJON bridge implemented as Arduino sketch

outstading features
- PJON serial strategy
  - receive without ACK from local bus [implementing]
  - receive with ACK
  - send without ACK to local bus
  - send with ACK
- public api
  - blocking
  - non-blocking
- auto-discover of serial-PJON bridge

v0.1 goals:
- local and remote serial port support with auto-discovery of the serial2pjon proxy arduino
- PJON serial strategy for local bus with ACK support

v0.2 goals:
- full PJON serial protocol for serial strategy (remote buses support)
