from unittest import TestCase

import fakeredis

from pjon_python.utils import fakeserial


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
