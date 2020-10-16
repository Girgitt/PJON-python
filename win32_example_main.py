from pjon_python import wrapper_client
import time

# this examples uses PJON-piper based clinet. expects device with address 201 responding to "ping" message with "pong" response

cli = pc = wrapper_client.PjonPiperClient(com_port='COM5', bus_addr=200, baud=115200)


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

cli.set_receiver(receive_handler)
cli.set_error(error_handler)
cli.start_client()

while True:
    out_queue_size = cli.send(201, "ping")
    if out_queue_size:
        print "pakets in outgoing queue: %s" % out_queue_size
    time.sleep(.5)