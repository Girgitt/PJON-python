from unittest import TestCase, skip

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
    @skip
    def test_serial_client_should_read_all_available_bytes_to_receive_buffer(self):
        with mock.patch('serial.Serial', create=True) as ser:
            def arr_return(size):
                vars = [chr(item) for item in [1, 9, 2, 45]]
                vars.reverse()
                return vars[:size]
            ser.read.side_effect = arr_return
            ser.inWaiting.side_effect = [4, 3, 2, 1]
            serial_strategy = PJONserialStrategy(serial_port=ser)
            self.assertEquals(serial_strategy.receive_byte(), 1)
            self.assertEquals(len(serial_strategy._read_buffer), 3)
            self.assertEquals(serial_strategy.receive_byte(), 9)
            self.assertEquals(len(serial_strategy._read_buffer), 2)
            self.assertEquals(serial_strategy.receive_byte(), 2)
            self.assertEquals(len(serial_strategy._read_buffer), 1)
            self.assertEquals(serial_strategy.receive_byte(), 45)
            self.assertEquals(len(serial_strategy._read_buffer), 0)
    @skip
    def test_serial_client_should_trim_serial_buffer(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_strategy = PJONserialStrategy(serial_port=ser)

            def return_payload_twice_the_buffer_length(size):
                vars = [chr(13)] * serial_strategy._READ_BUFFER_SIZE * 2
                return vars[:size]

            ser.read.side_effect = return_payload_twice_the_buffer_length
            ser.inWaiting.side_effect = [len(return_payload_twice_the_buffer_length(serial_strategy._READ_BUFFER_SIZE * 2))]

            self.assertEqual(serial_strategy.receive_byte(), 13)

            self.assertEqual(len(serial_strategy._read_buffer), 32767)

