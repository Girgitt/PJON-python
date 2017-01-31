from pjon_python.base_client import PjonBaseSerialClient
import time

# load serial2pjon_proxy_v5_1 to arduino
# adjust serial port below to match your arduino's port
# run this example; expected output:
#
# pakets in outgoing queue: 0
# received from 35 payload: [66, 49, 50, 51, 52, 53, 54, 55, 56, 57]
# pakets in outgoing queue: 0
# pakets in outgoing queue: 0
# received from 35 payload: [66, 49, 50, 51, 52, 53, 54, 55, 56, 57]
# pakets in outgoing queue: 0
#

cli = PjonBaseSerialClient(1, '/dev/ttyUSB1', write_timeout=0.005, timeout=0.005)


def error_handler(self, error_code=0, parameter=0):
    error_text = "code: %s, parameter: %s" % (error_code, parameter)
    if error_code == 101:
        error_text = "connection lost to node: %s" % parameter
    elif error_code == 101:
        error_text = "outgoing buffer full"

    if error_code > 0:
        print(error_text)

def receive_handler(payload, packet_length, packet_info):
    print "received from %s payload: %s" % (packet_info.sender_id, payload)

cli.set_receive(receive_handler)
cli.set_error(error_handler)
cli.start_client()

while True:
    print "pakets in outgoing queue: %s" % cli.send(35, "C123")
    time.sleep(.1)