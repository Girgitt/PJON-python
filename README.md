# PJON-python
Pythonic interface to PJON communication protocol.

Current status: 
- work in progress, minimal client operational but requires PJON with enhanced serial strategy to support multi-master operation e.g. on RS485 bus
- initially PHY abstraction to BitBang and OverSampling strategies provided by a serial-PJON bridge implemented as Arduino sketch
- HardwareSerial strategy for HALF_DUPLEX, multi-master communication mode e.g. over RS485 bus is provided directly (serial-RS485 converter required)
- HardwareSerial strategy for SIMPLEX communication mode will be provided directly (e.g. to talk to a single Arduino)

outstading features
- PJON serial strategy
  - receive without ACK from local bus [done]
  - receive with ACK [done]
  - send without ACK to local bus [done]
  - send with ACK [done]
- PJON protocol
  - receive [done]
  - send [done]
  - update [done]
  - repetitive send
  - local bus support [done]
  - shared bus support
- public api
  - blocking [implementing]
  - non-blocking [done]
- auto-discover of serial-PJON bridge

v0.1 goals:
- local and remote serial port support with auto-discovery of the serial2pjon proxy arduino
- PJON serial strategy for local bus with ACK support

v0.2 goals:
- full PJON serial protocol for serial strategy (remote buses support)


minimal client example
```python
from pjon_python.base_client import PjonBaseSerialClient
import time

pjon_cli = PjonBaseSerialClient(1, 'COM6')
pjon_cli.start_client()


def receive_handler(payload, packet_length, packet_info):
    print "received packet from device %s with payload: %s" % (packet_info.sender_id, payload)

pjon_cli.set_receive(receive_handler)

while True:
    #             recipient id   payload
    pjon_cli.send(35,            'C123456789')
    time.sleep(1)
```