from pjon_python import serial_utils
import serial
import time
from pjon_python import crc8
from pjon_python import pjon_protocol
from pjon_python import pjon_hwserial_strategy
import logging
from threading import Thread

"""
NOT IMPLEMENTED; it's just fooling around; refer to pjon_protocol for working implementation
"""

bridge_id_response = [hex(ord(item)) for item in 'i_am_serial2pjon']
bridge_id_query = [hex(ord(item)) for item in 'are_you_serial2pjon']

log = logging.getLogger("base-cli")


class PjonIoUpdateThread(Thread):
    def __init__(self, pjon_protocol):
        super(PjonIoUpdateThread, self).__init__()
        self._pjon_protocol = pjon_protocol

    def run(self):
        iter_cnt = 0
        while True:
            if iter_cnt % 1 == 0:
                self._pjon_protocol.update()
            self._pjon_protocol.receive()
            time.sleep(0.001)
            iter_cnt += 1


class PjonBaseSerialClient(object):
    """
    This class is a base for sync and async clients
    It provides reading and writing threads communicating through queues

    If com port is not specified it's assumed serial2pjon proxy is used and all available
    COM ports are scanned trying to discover the proxy.
    """
    def __init__(self, bus_addr=1, com_port=None, baud=115200, write_timeout=0.2, timeout=0.2):
        if com_port is None:
            raise NotImplementedError("COM port not defined and serial2proxy not supported yet")
            #self._com_port = self.discover_proxy()
        available_com_ports = serial_utils.get_serial_ports()
        if com_port not in available_com_ports:
            raise EnvironmentError("specified COM port is one of available ports: %s" % available_com_ports)

        self._serial = serial.Serial(com_port, baud, write_timeout=write_timeout, timeout=timeout)

        serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(self._serial)
        self._protocol = pjon_protocol.PjonProtocol(bus_addr, strategy=serial_hw_strategy)

        self._started = False

    def set_receive(self, receive_function):
        self._protocol.set_receiver(receive_function)

    def set_error(self, error_function):
        self._protocol.set_error(error_function)

    def send(self, device_id, payload):
        return self._protocol.send(device_id, payload)

    def send_without_ack(self, device_id, payload):
        header = self._protocol.get_overridden_header(request_ack=False)
        return self._protocol.dispatch(device_id, payload, header=header)

    def start_client(self):
        if self._started:
            log.info('client already started')
            return
        io_thd = PjonIoUpdateThread(self._protocol)

        io_thd.setDaemon(True)

        io_thd.start()

    def discover_proxy(self):
        for com_port_name in serial_utils.get_serial_ports():
            print("checking port: %s" % com_port_name)
            ser = serial.Serial(com_port_name, 115200, write_timeout=0.2, timeout=0.5)
            try:
                if ser.closed:
                    print("openning")
                    ser.open()

                time.sleep(2.5)
                ser.flushInput()
                ser.flushOutput()

                #  remaining_bytes : session | CMD | d.a.t.a : CRC8 \n

                packet_input = [ord('\r'),
                          14,
                          ord(':'), ord('R'),
                          ord('|'), ord('C'),
                          ord('|'), 1, 2, 3, 4, 5, 6,
                          ord('|'), ord('8'),
                          ord('\n')]
                hex_string = "".join("%02x" % b for b in packet_input)

                #ser.write(hex_string.decode('hex'))
                print("hex arr: %s" % packet_input)

                print("writing")
                #ser.flushInput()
                #ser.flushOutput()
                ser.write(bytearray(packet_input))
                #ser.flushInput()

                resp = ""
                read_val = ""
                print("reading")
                while True:
                    read_val = ser.read(1)
                    if len(read_val) == 0:
                        break
                    resp += read_val

                print("%s resp>%s<" % (com_port_name, resp))
                return resp
            except serial.SerialException:
                import traceback
                traceback.print_exc(100)
            finally:
                try:
                    ser.close()
                    print("closing")
                except serial.SerialException:
                    traceback.print_exc(100)

        return None


    def listen_serial(self, timeout=5):
        # for com_port_name in serial_utils.get_serial_ports():
        for com_port_name in ['COM31']:
            print("checking port: %s" % com_port_name)
            ser = serial.Serial(com_port_name, 115200, write_timeout=0.2, timeout=0.5)
            try:
                if ser.closed:
                    print("openning")
                    ser.open()

                #time.sleep(3)
                ser.flushInput()
                ser.flushOutput()
                start_ts = time.time()
                resp = ""
                while True:
                    read_val = ser.read(1)
                    if len(read_val) == 0:
                        break
                    resp += str(ord(read_val))+"|"
                    if time.time() - start_ts > timeout:
                        break
                print(resp)

                #crc = crc8.crc8()
                #crc.update(''.join([chr(item) for item in [1,8,2,45,66,66,66,66]]))
                #print ord(crc.digest())
                crc = 0
                for b in [1,9,2,45,65,65,65,65]:
                    #for b in [1,8,2,45,65,66,67]:
                    #for b in [1,21,2,45,49,97,50,115,51,100,52,102,53,103,54,104,55,106,56,107]:
                    crc = crc8.AddToCRC(b, crc)
                print(crc)


            except serial.SerialException:
                import traceback
                traceback.print_exc(100)
            finally:
                try:
                    ser.close()
                    print("closing")
                except serial.SerialException:
                    traceback.print_exc(100)