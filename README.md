# PJON-python
Pythonic interface to PJON communication protocol.

Current status: 
- work in progress
- initially PHY abstraction provided by a serial-PJON bridge implemented as Arduino sketch
- finally to be extended by a native python-level implementation for serial communication stategy 

outstading features
- serial communication support utilizing serial port buffer
 - direct serial port
   - with auto-scanning
 - remote (RCF2217 over telnet using ser2net on Raspberry PI)
- serial protocol design
  - sending with validation/ack and message length control + timeout on uc side
  - receiving with validation/ack and message length control + timeout on pc side
  - re-transmit on both sides
- public api
  - blocking
  - non-blocking

v0.1 goals:
- local and remote serial port support with auto-discovery of the serial2pjon proxy arduino
- simplified pc-bridge serial protocol (probably termination sequence + timeout to control frames' end; no ack; no re-transmit)

v0.2 goals:
- enhanced serial protocol with proper frame length detection, ack and re-transmission
