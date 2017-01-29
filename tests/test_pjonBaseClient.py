from unittest import TestCase, skip
from unittest2.compatibility import wraps
from pjon_python import base_client

import time
import platform
import logging
log = logging.getLogger("tests")


def skip_if_condition(condition, reason):
    def deco(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if condition:
                self.skipTest(reason)
            else:
                f(self, *args, **kwargs)
        return wrapper
    return deco


class TestPjonBaseClient(TestCase):
    def setUp(self):
        self.is_arm = True if platform.platform().find('armv') > 0 else False
        self.cli_1 = base_client.PjonBaseSerialClient(bus_addr=1, com_port='fakeserial')
        self.cli_1.start_client()
        self.cli_2 = base_client.PjonBaseSerialClient(bus_addr=2, com_port='fakeserial')
        self.cli_2.start_client()
        self.cli_3 = base_client.PjonBaseSerialClient(bus_addr=3, com_port='fakeserial')
        self.cli_3.start_client()

    def test_fake_serial_should_pass_messages_between_clients_no_ack(self):
        self.cli_1.send_without_ack(2, 'test1')
        self.cli_1.send_without_ack(2, 'test2')
        time.sleep(.4)
        self.assertEquals(2, len(self.cli_2._protocol._stored_received_packets))

    @skip_if_condition(platform.platform().find('armv') > 0, 'skipping on ARM due to performance')
    def test_fake_serial_should_pass_messages_between_clients_with_ack(self):
        self.cli_1.send(2, 'test1')
        self.cli_1.send(2, 'test2')
        self.cli_1.send(3, 'test3')

        time.sleep(.8)
        self.assertEquals(2, len(self.cli_2._protocol._stored_received_packets))
        self.assertEquals(1, len(self.cli_3._protocol._stored_received_packets))

