import pjon_protocol_constants
import time
import logging

log = logging.getLogger("ser-strat")

THROUGH_HARDWARE_SERIAL_MAX_TIME_TO_WAIT_FOR_BYTE = 0.001
THROUGH_HARDWARE_SERIAL_MIN_TIME_CHANNEL_CLEARANCE = 0.001


class UnsupportedPayloadType(Exception):
    pass


class PJONserialStrategy(object):
    def __init__(self, serial_port=None):
        if serial_port is None:
            raise NotImplementedError("serial==None but autodiscovery of serial-pjon proxy is not imeplemented yet")
        else:
            log.info("passed serial port %s" % serial_port)
            self._ser = serial_port
            if self._ser.closed:
                log.debug("openning serial")
                self._ser.open()

            # time.sleep(3)
            self._ser.flushInput()
            self._ser.flushOutput()

        self._last_received_ts = 0

    def can_start(self):
        if self._ser:
            if time.time() - self._last_received_ts > THROUGH_HARDWARE_SERIAL_MIN_TIME_CHANNEL_CLEARANCE:
                return True
        return False

    def send_byte(self, b):
        try:
            if type(b) is str and len(b) == 1:
                log.debug("sending byte: %s (%s)" % (b, ord(b)))
                self._ser.write(b)
            elif type(b) is int:
                b = chr(b)
                if type(b) is str and len(b) == 1:
                    log.debug("sending byte: %s (%s)" % (b, ord(b)))
                    self._ser.write(b)
                else:
                    raise TypeError
            else:
                raise TypeError
        except TypeError:
                raise UnsupportedPayloadType("byte type should be str length 1 or int but %s found" % type(b))
        return 0

    def receive_byte(self):
        # FIXME: move serial port reading to thread reading input to queue and change receive_byte to read from queue
        log.debug("    >>> rcv byte")
        start_time = time.time()
        while time.time() - start_time < THROUGH_HARDWARE_SERIAL_MAX_TIME_TO_WAIT_FOR_BYTE:
            try:
                bytes_waiting = self._ser.inWaiting()
                if True:
                    #if bytes_waiting > 0:  #  bug in pyserial? for single byte 0 is returned
                    log.debug("     >> waiting bytes: %s" % bytes_waiting)
                    rcv_val = self._ser.read(1)
                    if rcv_val != '':
                        log.debug("      > received byte: %s (%s)" % (ord(rcv_val), rcv_val))
                        self._last_received_ts = time.time()
                        return ord(rcv_val)
            except StopIteration:  # needed for mocking in unit tests
                pass

        return pjon_protocol_constants.FAIL

    def receive_response(self):
        return self.receive_byte()

    def send_response(self, response):
        self.send_byte(response)


