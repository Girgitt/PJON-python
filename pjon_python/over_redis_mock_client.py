from pjon_python.utils.RedisConn import RedisConn
import uuid
import logging
import threading
import fakeredis
from pjon_python.protocol.pjon_protocol import PacketInfo
from pjon_python.protocol.pjon_protocol import ReceivedPacket

log = logging.getLogger("over_redis")

fake_redis_cli = fakeredis.FakeStrictRedis()
instance_id = 0


class OverRedisClient(object):
    """ class which uses redis (or fakeredis) pub/sub to communicate with other serial
    redis clients. It's purpose is to enable PJON-like communication without
    OS-level serial port emulators.
    """

    def __init__(self, bus_addr=1, com_port=None, baud=115200, transport=None):

        global instance_id
        instance_id += 1
        self._uuid = str(uuid.uuid4())
        if transport is None:

            self._transport = RedisConn(fake_redis_cli,
                                       sub_channel='pjon-python-redis',
                                       pub_channel='pjon-python-redis',
                                       cli_id=self._uuid)
            log.debug("using fakeredis transport")
        else:
            self._transport = RedisConn(transport,
                                       sub_channel='pjon-python-redis',
                                       pub_channel='pjon-python-redis')
        log.debug("using transport: %s" % str(transport))

        #self.transport.subscribe('pjon-serial')
        self._transport.subscribe('pjon-python-redis')

        self._data = []
        self._started = False
        self._bus_addr = bus_addr
        self._receiver_function = self.dummy_receiver
        self._error_function = self.dummy_error

    @staticmethod
    def dummy_receiver(*args, **kwargs):
        pass

    @staticmethod
    def dummy_error(*args, **kwargs):
        pass

    def set_receiver(self, receiver_function):
        self._receiver_function = receiver_function

    def set_error(self, error_function):
        self._error_function = error_function

    def start_client(self):
        if self._started:
            log.info('client already started')
            return
        log.debug("starting update redis input thd")
        self._started = True
        run_thd = threading.Thread(target=self.update_redis_input)
        run_thd.daemon = True
        run_thd.start()

    def stop_client(self):
        self._started = False

    def write(self, string):
        message = dict()
        message['originator_uuid'] = self._uuid
        message['payload'] = string
        self._transport.publish(message)

    def send(self, receiver_id, payload, sender_id=None):
        log.debug("sending %s to %s" % (payload, receiver_id))
        packet_message = dict()
        packet_message['originator_uuid'] = self._uuid
        packet_message['receiver_id'] = receiver_id
        packet_message['receiver_bus_id'] = [0, 0, 0, 0]
        if sender_id is None:
            packet_message['sender_id'] = self._bus_addr
        else:
            packet_message['sender_id'] = sender_id
        packet_message['sender_bus_id'] = [0, 0, 0, 0]
        packet_message['payload'] = payload
        packet_message['payload_length'] = len(payload)
        self._transport.publish(packet_message)

    def send_without_ack(self, device_id, payload):
        self.send_without_ack(device_id, payload)

    def send_with_forced_sender_id(self, receiver_id, sender_id, payload):
        self.send(receiver_id, payload, sender_id=sender_id)

    @staticmethod
    def get_packet_info_obj_for_packet_message(packet_message):
        packet_info = PacketInfo()
        PacketInfo.receiver_id = packet_message['receiver_id']
        PacketInfo.receiver_bus_id = packet_message['receiver_bus_id']
        PacketInfo.sender_id = packet_message['sender_id']
        PacketInfo.sender_bus_id = packet_message['sender_bus_id']
        payload = packet_message['payload']
        length = packet_message['payload_length']

        return ReceivedPacket(payload=payload, packet_length=length, packet_info=packet_info)

    def update_redis_input(self):
        while True:
            if not self._started:
                return
            new_message = self._transport.listen(rcv_timeout=0.01)
            if new_message:
                if new_message['originator_uuid'] != self._uuid:
                    packet = self.get_packet_info_obj_for_packet_message(new_message)
                    payload = packet.payload_as_string
                    packet_length = packet.packet_length
                    packet_info = packet.packet_info
                    if packet_info.receiver_id != 0:
                        if packet_info.receiver_id != self._bus_addr:
                            log.debug("packet for someone else: %s" % str(packet_info))
                            continue
                    self._receiver_function(payload, packet_length, packet_info)
                else:
                    pass
                    #log.debug("received own msg")

    def __str__(self):
        return "OverRedisClient, transport: %s" % str(self._transport)
