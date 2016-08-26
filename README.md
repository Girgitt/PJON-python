# PJON-python
Pythonic interface to PJON communication protocol.

Current status: 
- work in progress
- initially PHY abstraction to BitBand and OverSampling strategies provided by a serial-PJON bridge implemented as Arduino sketch
- HardwareSerial strategy for HALF_DUPLEX, multi-master communication mode e.g. over RS485 bus will be provided directly (serial-RS485 converter required)
- HardwareSerial strategy for SIMPLEX communication mode will be provided directly (e.g. to talk to a single Arduino)

outstading features
- PJON serial strategy
  - receive without ACK from local bus [done]
  - receive with ACK [done]
  - send without ACK to local bus [implementing]
  - send with ACK [implementing]
- public api
  - blocking
  - non-blocking
- auto-discover of serial-PJON bridge

v0.1 goals:
- local and remote serial port support with auto-discovery of the serial2pjon proxy arduino
- PJON serial strategy for local bus with ACK support

v0.2 goals:
- full PJON serial protocol for serial strategy (remote buses support)
