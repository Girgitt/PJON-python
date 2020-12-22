from unittest import TestCase
import mock
import time
import json
import fakeredis

from pjon_python.utils import fakeserial
from pjon_python import over_redis_mock_client


class TestSerialOverRedis(TestCase):
    def setUp(self):
        redis_cli = fakeredis.FakeStrictRedis()
        self.ser_cli_1 = fakeserial.Serial(port='COM1', baudrate=9600,
                                           transport=redis_cli)

        self.ser_cli_2 = fakeserial.Serial(port='COM1', baudrate=9600,
                                           transport=redis_cli)

    def test_write__should_deliver_to_other_clients_but_not_to_originator(self):
        self.ser_cli_1.write('a')
        self.assertEquals(['a'], self.ser_cli_2.read())
        self.assertEquals([], self.ser_cli_1.read())

        self.ser_cli_1.write('abc')
        self.assertEquals(3, self.ser_cli_2.inWaiting())
        self.assertEquals(['a'], self.ser_cli_2.read())
        self.assertEquals(['b'], self.ser_cli_2.read())
        self.assertEquals(['c'], self.ser_cli_2.read())
        self.assertEquals(0, self.ser_cli_2.inWaiting())

        self.assertEquals(0, self.ser_cli_1.inWaiting())
        self.assertEquals([], self.ser_cli_1.read())

    def test_redis_client__should_call_receive_function_when_receives_publish_msg_with_own_id_as_receiver(self):
        redis_cli = fakeredis.FakeStrictRedis()
        with mock.patch('pjon_python.over_redis_mock_client.OverRedisClient.dummy_receiver_forward', create=True) as rcv_fwd_mock:
            with mock.patch('pjon_python.over_redis_mock_client.OverRedisClient.dummy_receiver', create=True) as rcv_mock:
                rc = over_redis_mock_client.OverRedisClient(com_port="COMX", bus_addr=99, baud=115200,
                                                            transport=redis_cli)
                rc.start_client()
                self.assertFalse(rcv_fwd_mock.called)
                self.assertFalse(rcv_mock.called)
                test_msg = {
                    "sender_bus_id": [0, 0, 0, 0],
                    "receiver_id": 99,
                    "payload_length": 10,
                    "sender_id": 22,
                    "receiver_bus_id": [0, 0, 0, 0],
                    "originator_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "payload": "B test 123"}
                redis_cli.publish('pjon-python-redis', json.dumps(test_msg))
                time.sleep(0.1)
                self.assertFalse(rcv_fwd_mock.called)
                self.assertTrue(rcv_mock.called)

    def test_redis_client__should_call_forward_function_when_receives_publish_msg_with_own_id_as_sender(self):
        redis_cli = fakeredis.FakeStrictRedis()
        with mock.patch('pjon_python.over_redis_mock_client.OverRedisClient.dummy_receiver_forward', create=True) as rcv_fwd_mock:
            with mock.patch('pjon_python.over_redis_mock_client.OverRedisClient.dummy_receiver', create=True) as rcv_mock:
                rc = over_redis_mock_client.OverRedisClient(com_port="COMX", bus_addr=99, baud=115200,
                                                            transport=redis_cli)
                rc.start_client()
                self.assertFalse(rcv_fwd_mock.called)
                self.assertFalse(rcv_mock.called)
                test_msg = {
                    "sender_bus_id": [0, 0, 0, 0],
                    "receiver_id": 22,
                    "payload_length": 10,
                    "sender_id": 99,
                    "receiver_bus_id": [0, 0, 0, 0],
                    "originator_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "payload": "B test 123"}
                redis_cli.publish('pjon-python-redis', json.dumps(test_msg))
                time.sleep(0.1)
                self.assertTrue(rcv_fwd_mock.called)
                self.assertFalse(rcv_mock.called)