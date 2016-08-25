import pjon_protocol_constants
import time
import logging

log = logging.getLogger("ser-strat")

THROUGH_HARDWARE_SERIAL_MAX_TIME = 0.01


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

    def can_start(self):
        if self._ser:
            return True
        return False

    def send_byte(self, b):
        self._ser.write(b)
        return 0

    def receive_byte(self):
        # FIXME: move serial port reading to thread reading input to queue and change receive_byte to read from queue
        log.debug("    >>> rcv byte")
        start_time = time.time()
        while time.time() - start_time < THROUGH_HARDWARE_SERIAL_MAX_TIME:
            try:
                bytes_waiting = self._ser.inWaiting()
                if True:
                    #if bytes_waiting > 0:  #  bug in pyserial? for single byte 0 is returned
                    log.debug("     >> waiting bytes: %s" % bytes_waiting)
                    rcv_val = self._ser.read(1)
                    if rcv_val != '':
                        log.debug("      > received byte: %s (%s)" % (ord(rcv_val), rcv_val))
                        return ord(rcv_val)
            except StopIteration:
                pass

        return pjon_protocol_constants.FAIL

    def receive_response(self):
        self.receive_byte()

    def send_response(self, response):
        self.send_byte(response)


