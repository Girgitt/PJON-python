PJON-python
===========

Pythonic interface to PJON communication protocol.

PJON (Github: `PJON <https://github.com/gioblu/PJON/>`__ ) is an
open-source, multi-master, multi-media (one-wire, two-wires, radio)
communication protocol available for various platforms (Arduino/AVR,
ESP8266, Teensy).

PJON is one of very few open-source implementations of multi-master
communication protocols for microcontrollers.

PJON-python module in the current status enables communication with
other PJON devices directly over UART (serial communication):

-  In a basic scenario PJON + PJON-python can be a viable alternative to
   more complex protocols like Firmata (Arduino firmware on Github:
   `firmata/Arduino <https://github.com/firmata/arduino>`__ for direct
   (SIMPLEX) communication host-uC.
-  If RS485 drivers with auto-tx setup are used the host (e.g. Raspberry
   PI) can join multi-master PJON bus and python programs can
   communicate with multiple uC.
-  If uC with proxy firmware (sending packets between serial and other
   type of PJON bus) is used the host can communicate with PJON buses
   other than serial through that serial2pjon proxy uC.

PJON-python module opens popular uC platforms (Arduino, ESP8266, Teensy)
to the whole range of applications: - multi-master automation (reporting
by exception lowers latency compared to polling-based protocols like
Modbus) - open-hardware IoT (thanks to integration flexibility of other
python modules)

Current status:
---------------

-  work in progress, minimal client operational with PJON v4.2 or v4.3
   (ThroughHardwareSerial strategy is required)
-  initially PHY abstraction to BitBang and OverSampling strategies
   provided by a serial-PJON bridge implemented as Arduino sketch
-  support for ThroughHardwareSerial strategy in HALF\_DUPLEX,
   multi-master communication mode e.g. over RS485 bus is provided
   directly (serial-RS485 converter required)
-  support for ThroughHardwareSerial strategy in SIMPLEX communication
   mode will be provided directly (e.g. to talk to a single Arduino).
-  Communication with a single arduino connected to USB works in
   HALF\_DUPLEX mode out of the box without any additional hardware

outstading features
-------------------

-  PJON serial strategy
-  receive without ACK from local bus [done]
-  receive with ACK [done]
-  send without ACK to local bus [done]
-  send with ACK [done]
-  PJON protocol
-  receive [done]
-  send [done]
-  update [done]
-  repetitive send
-  local bus support [done]
-  including sender ID [done]
-  shared bus support
-  auto addressing (PJON v5 feature)
-  public api
-  blocking [implementing]
-  non-blocking [done]
-  auto-discover of serial-PJON bridge

PJON-python versions are aligned with PJON versions to indicate
compatibility with C implementation for uC platforms.

v4 goals:
^^^^^^^^^

-  local and remote serial port support with auto-discovery of the
   serial2pjon proxy arduino
-  PJON serial strategy for local bus with ACK support [done]
-  full PJON serial protocol for serial strategy (remote buses support)

v5 goals:
^^^^^^^^^

-  auto addressing

minimal client example

.. code:: python

    from pjon_python.base_client import PjonBaseSerialClient
    import time

    pjon_cli = PjonBaseSerialClient(1, 'COM6')
    pjon_cli.start_client()


    def receive_handler(payload, packet_length, packet_info):
        print "received packet from device %s with payload: %s" % (packet_info.sender_id, payload)

    pjon_cli.set_receive(receive_handler)

    while True:
        #             recipient id   payload
        pjon_cli.send(35,            'C123456789')  # payload can be string or an array of bytes (or any type suitable for casting to byte)
        time.sleep(1)
