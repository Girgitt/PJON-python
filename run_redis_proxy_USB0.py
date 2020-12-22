import time
import redis
import logging

from pjon_python import over_redis_mock_client
from pjon_python import wrapper_client

logging.basicConfig()
logging.getLogger().setLevel(logging.ERROR)


log = logging.getLogger('main')
log.addHandler(logging.NullHandler())
log.setLevel(logging.INFO)

# This example shows how to communicate with serial a PJON device over Redis pub/sub queues
# It enables asynchronous communication between PJON nodes and e.g. Node-Red where logic can be easily implemented


# redis-side specification
# pub/sub channel: pjon-python-redis
# send message:
"""
{
    "payload": "TX_SHUTDOWN",
    "payload_length": 11,
    "originator_uuid": "0",
    "receiver_id": 201,
    "receiver_bus_id": [
        0,
        0,
        0,
        0
    ],
    "sender_id": 200,
    "sender_bus_id": [
        0,
        0,
        0,
        0
    ]
}
"""


def receive_handler_redis(payload, packet_length, packet_info):
    log.info("received packet from device %s with payload: %s" % (packet_info.sender_id, payload))


def receive_forward_handler_redis(payload, packet_length, packet_info):
    log.info("forwarding packet to device %s with payload: %s" % (packet_info.receiver_id, payload))
    pjon_client.send(packet_info.receiver_id, payload)


def error_handler_redis(error_code, parameter):
    log.error("PJON error occurred,code: %s parameter: %s" % (error_code, parameter))


def receive_handler_serial(payload, packet_length, packet_info):
    log.info("received packet from device %s with payload: %s" % (packet_info.sender_id, payload))
    redis_client.send(packet_info.receiver_id, payload, sender_id=packet_info.sender_id)


def error_handler_serial(error_code, parameter):
    log.error("PJON error occurred,code: %s parameter: %s" % (error_code, parameter))


redis_cli = redis.StrictRedis(host="127.0.0.1", port=6379)

redis_client = over_redis_mock_client.OverRedisClient(com_port='COMX', bus_addr=200, baud=115200, transport=redis_cli)
pjon_client = wrapper_client.PjonPiperClient(com_port='/dev/ttyCH340', bus_addr=200, baud=115200)


redis_client.set_receiver(receive_handler_redis)
redis_client.set_receiver_forward(receive_forward_handler_redis)
redis_client.set_error(error_handler_redis)

redis_client.start_client()

pjon_client.set_receiver(receive_handler_serial)
pjon_client.set_error(error_handler_serial)
pjon_client.set_piper_stdout_watchdog(timeout_sec=10)  # setting a watchdog which restarts PJON-piper client if no packet arrived for 10s

pjon_client.start_client()


try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    redis_client.stop_client()
    pjon_client.stop_client()
