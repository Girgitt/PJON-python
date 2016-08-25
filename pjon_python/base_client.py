import serial_utils
import serial
import time
from pjon_python import crc8

"""
NOT IMPLEMENTED; it's just fooling around; refer to pjon_protocol for working implementation
"""

bridge_id_response = [hex(ord(item)) for item in 'i_am_serial2pjon']
bridge_id_query = [hex(ord(item)) for item in 'are_you_serial2pjon']


class PjonBaseClient(object):
    def __init__(self):
        pass

    def discover_proxy(self):
        #for com_port_name in serial_utils.get_serial_ports():
        for com_port_name in ['COM6']:
            print "checking port: %s" % com_port_name
            ser = serial.Serial(com_port_name, 115200, write_timeout=0.2, timeout=0.5)
            try:
                if ser.closed:
                    print "openning"
                    ser.open()

                time.sleep(3)
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
                print "hex arr: %s" % packet_input

                print "writing"
                #ser.flushInput()
                #ser.flushOutput()
                ser.write(bytearray(packet_input))
                #ser.flushInput()

                resp = ""
                read_val = ""
                print "reading"
                while True:
                    read_val = ser.read(1)
                    if len(read_val) == 0:
                        break
                    resp += read_val

                print "%s resp>%s<" % (com_port_name, resp)
                return resp
            except serial.SerialException:
                import traceback
                traceback.print_exc(100)
            finally:
                try:
                    ser.close()
                    print "closing"
                except serial.SerialException:
                    traceback.print_exc(100)

        return None


    def listen_serial(self, timeout=5):
        # for com_port_name in serial_utils.get_serial_ports():
        for com_port_name in ['COM31']:
            print "checking port: %s" % com_port_name
            ser = serial.Serial(com_port_name, 115200, write_timeout=0.2, timeout=0.5)
            try:
                if ser.closed:
                    print "openning"
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
                print resp

                #crc = crc8.crc8()
                #crc.update(''.join([chr(item) for item in [1,8,2,45,66,66,66,66]]))
                #print ord(crc.digest())
                crc = 0
                for b in [1,9,2,45,65,65,65,65]:
                    #for b in [1,8,2,45,65,66,67]:
                    #for b in [1,21,2,45,49,97,50,115,51,100,52,102,53,103,54,104,55,106,56,107]:
                    crc = crc8.AddToCRC(b, crc)
                print crc


            except serial.SerialException:
                import traceback
                traceback.print_exc(100)
            finally:
                try:
                    ser.close()
                    print "closing"
                except serial.SerialException:
                    traceback.print_exc(100)