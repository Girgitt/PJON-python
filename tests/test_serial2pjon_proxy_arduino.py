from unittest import TestCase
from pjon_python.base_client import PjonBaseSerialClient


class TestSerial2pjonProxy(TestCase):
    def setUp(self):
        self.cli = PjonBaseSerialClient(1, '/dev/ttyUSB1')
        self.cli.start_client()

    def test_proxy_should_respond(self):
        import time
        for i in range(5):
            self.cli.send_without_ack(35, 'C12345')
            #self.cli.send(35, 'A12345')
            time.sleep(0.1)
        self.fail()
