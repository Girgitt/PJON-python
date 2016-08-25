from unittest import TestCase, skip
from pjon_python import base_client


class TestPjonBaseClient(TestCase):
    def setUp(self):
        self.cli = base_client.PjonBaseClient()
    @skip
    def test_base_client_should_detect_proxy_on_local_com(self):
        self.assertEquals("ddd", self.cli.discover_proxy())

    @skip
    def test_listen(self):
        self.cli.listen_serial()
        self.fail()
