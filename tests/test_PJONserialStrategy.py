from unittest import TestCase

import mock

from pjon_python.strategies.pjon_hwserial_strategy import PJONserialStrategy, UnsupportedPayloadType


class TestPJONserialStrategy(TestCase):

    def test_send_byte_should_convert_int_to_chr(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_strategy = PJONserialStrategy(serial_port=ser)

            self.assertEquals(serial_strategy.send_byte(11), 0)

    def test_send_byte_should_convert_hex_to_chr(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_strategy = PJONserialStrategy(serial_port=ser)
            self.assertEquals(serial_strategy.send_byte(0x22), 0)

    def test_send_byte_should_accept_char(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_strategy = PJONserialStrategy(serial_port=ser)
            self.assertEquals(serial_strategy.send_byte('a'), 0)

    def test_send_byte_should_raise_on_unsupported_type(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_strategy = PJONserialStrategy(serial_port=ser)
            self.assertRaises(UnsupportedPayloadType, serial_strategy.send_byte, ['a', 'b'])
            self.assertRaises(UnsupportedPayloadType, serial_strategy.send_byte, 'abc')
            self.assertRaises(UnsupportedPayloadType, serial_strategy.send_byte, [1, 2])
            self.assertRaises(UnsupportedPayloadType, serial_strategy.send_byte, {'a': 'b'})
