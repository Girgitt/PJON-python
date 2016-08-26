from unittest import TestCase, skip
from pjon_python import pjon_protocol
from pjon_python import pjon_hwserial_strategy
from pjon_python import pjon_protocol_constants
import serial
import time
import mock
import logging


log = logging.getLogger("tests")


class TestPjonProtocol(TestCase):
    def setUp(self):
        self.rcvd_packets = []

    def print_args(*args, **kwargs):
        log.debug(">> print args")
        for arg in args:
            log.debug("arg: %s" % arg)
        for key, value in kwargs.iteritems():
            log.debug("kwarg: %s=%s" % (key, value))

    def test_crc_should_be_calcualted_for_single_char_str(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            self.assertEquals(59, proto.compute_crc_8_for_byte('a', 0))

    def test_crc_should_be_calcualted_for_int(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            self.assertEquals(28, proto.compute_crc_8_for_byte(37, 0))

    def test_crc_should_raise_on_unsupported_types(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            self.assertRaises(TypeError, proto.compute_crc_8_for_byte, ['a', 'b'], 0)
            self.assertRaises(TypeError, proto.compute_crc_8_for_byte, 'ab', 0)
            self.assertRaises(TypeError, proto.compute_crc_8_for_byte, {'a': 2}, 0)

    def test_packet_info__should_interpret_bits_correctly(self):
        with mock.patch('serial.Serial', create=True) as ser:
            ser.read.side_effect = [chr(item) for item in [1, 9, 2, 45, 65, 65, 65, 65, 71]]
            ser.inWaiting.side_effect =                   [9, 8, 7,  6,  5,  4,  3,  2,  1, 0]
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)

            local_packet_no_ack = [1, 8, 2, 45, 65, 66, 67, 198]

            packet_info = proto.get_packet_info(local_packet_no_ack)

            self.assertEquals(45, packet_info.sender_id)
            self.assertEquals(1, packet_info.receiver_id)
            self.assertEquals(2, packet_info.header)

    def test_receive_should_get_packet_from_local_bus(self):
        with mock.patch('serial.Serial', create=True) as ser:
            ser.read.side_effect = [chr(item) for item in [1, 9, 2, 45, 65, 65, 65, 65, 71]]
            ser.inWaiting.side_effect =                   [9, 8, 7,  6,  5,  4,  3,  2,  1, 0]
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            proto.receiver_function(self.print_args)

            timeout = 0.05
            start_ts = time.time()
            while True:
                proto.receive()
                if time.time() - start_ts > timeout:
                    break

            self.assertEquals(1, len(proto._stored_received_packets))
            self.assertEquals(1, proto._stored_received_packets[-1].packet_info.receiver_id)
            self.assertEquals(45, proto._stored_received_packets[-1].packet_info.sender_id)
            self.assertEquals([65, 65, 65, 65], proto._stored_received_packets[-1].payload)
            self.assertEquals(9, proto._stored_received_packets[-1].packet_length)

    def test_receive_should_get_multiple_packets_from_local_bus(self):
        with mock.patch('serial.Serial', create=True) as ser:
            ser.read.side_effect = [chr(item) for item in [1, 9, 2, 45, 65, 65, 65, 65, 71,    1, 8, 2, 100, 61, 62, 63, 65]]
            ser.inWaiting.side_effect =                   [9, 8, 7,  6,  5,  4,  3,  2,  1, 0, 8, 7, 6,   5,  4,  3,  2,  1, 0]
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            proto.receiver_function(self.print_args)

            timeout = 0.05
            start_ts = time.time()
            while True:
                proto.receive()
                if time.time() - start_ts > timeout:
                    break

            self.assertEquals(2, len(proto._stored_received_packets))
            self.assertEquals(1, proto._stored_received_packets[-1].packet_info.receiver_id)
            self.assertEquals(100, proto._stored_received_packets[-1].packet_info.sender_id)
            self.assertEquals([61, 62, 63], proto._stored_received_packets[-1].payload)
            self.assertEquals(8, proto._stored_received_packets[-1].packet_length)

    def test_protocol_client_should_truncate_received_packets_buffer(self):
        with mock.patch('serial.Serial', create=True) as ser:
            single_packet = [chr(item) for item in [1, 9, 2, 45, 65, 65, 65, 65, 71]]
            multiple_packets = []
            packets_count = 50
            for i in xrange(packets_count):
                multiple_packets.extend(single_packet)

            self.assertEquals(packets_count * len(single_packet), len(multiple_packets))

            ser.read.side_effect = multiple_packets
            log.debug(multiple_packets)
            bytes_count_arr = []
            for i in xrange(len(multiple_packets)+1):
                bytes_count_arr.append(i)

            bytes_count_arr.reverse()
            log.debug(bytes_count_arr)
            self.assertEquals(bytes_count_arr[0], len(multiple_packets))
            self.assertEquals(bytes_count_arr[-1], 0)
            ser.inWaiting.side_effect = bytes_count_arr

            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            proto.receiver_function(self.print_args)
            proto._received_packets_buffer_length = 8

            timeout = 0.05
            start_ts = time.time()
            while True:
                proto.receive()
                if time.time() - start_ts > timeout:
                    break

            self.assertEquals(proto._received_packets_buffer_length, len(proto._stored_received_packets))
            self.assertEquals(1, proto._stored_received_packets[-1].packet_info.receiver_id)
            self.assertEquals(45, proto._stored_received_packets[-1].packet_info.sender_id)
            self.assertEquals([65, 65, 65, 65], proto._stored_received_packets[-1].payload)
            self.assertEquals(9, proto._stored_received_packets[-1].packet_length)

    @skip
    def test_receive_should_get_packets_from_real_hardware(self):
        ser = serial.Serial('COM31', 115200, write_timeout=0.2, timeout=0.5)

        log.debug(">>> strategy init")
        serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
        log.debug("<<< strategy init")
        proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
        # self.assertEquals(pjon_protocol_constants.ACK, proto.receive())

        timeout = 1.5
        start_ts = time.time()
        while True:
            proto.receive()
            if time.time() - start_ts > timeout:
                break

        self.assertEquals(1, proto._stored_received_packets[-1].packet_info.receiver_id)
        self.assertEquals(45, proto._stored_received_packets[-1].packet_info.sender_id)
        self.assertEquals([65, 65, 65, 65], proto._stored_received_packets[-1].payload)
        self.assertEquals(9, proto._stored_received_packets[-1].packet_length)

    @skip
    def test_receive_should_get_packets_from_real_hardware_2(self):
        ser = serial.Serial('COM6', 115200, write_timeout=0.2, timeout=0.5)
        time.sleep(2.5)
        log.debug(">>> strategy init")
        serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
        log.debug("<<< strategy init")
        proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
        # self.assertEquals(pjon_protocol_constants.ACK, proto.receive())

        timeout = 2
        start_ts = time.time()
        while True:
            proto.receive()
            if time.time() - start_ts > timeout:
                break

        self.assertEquals(1, proto._stored_received_packets[-1].packet_info.receiver_id)
        self.assertEquals(35, proto._stored_received_packets[-1].packet_info.sender_id)
        self.assertEquals([65, 65, 65, 65], proto._stored_received_packets[-1].payload)
        self.assertEquals(9, proto._stored_received_packets[-1].packet_length)

    def test_protocol_client_should_send_packets_with_ack(self):
        with mock.patch('serial.Serial', create=True) as ser:
            log.debug(">>> strategy init")
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            log.debug("<<< strategy init")
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)

            ser.read.side_effect = [chr(pjon_protocol_constants.ACK)]

            self.assertEquals(pjon_protocol_constants.ACK, proto.send_string(1, "test"))

            self.assertEquals(8, ser.write.call_count)
            self.assertEquals(1, ser.read.call_count)

    def test_protocol_client_should_send_packets_without_ack(self):
        with mock.patch('serial.Serial', create=True) as ser:
            log.debug(">>> strategy init")
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            log.debug("<<< strategy init")
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            proto.set_acknowledge(False)
            ser.read.side_effect = ['1']

            self.assertEquals(pjon_protocol_constants.ACK, proto.send_string(1, "test"))

            self.assertEquals(8, ser.write.call_count)
            self.assertEquals(0, ser.read.call_count)
    @skip
    def test_send_string__should_send_packet_without_ack_to_real_hardware(self):
        ser = serial.Serial('COM6', 115200, write_timeout=0.2, timeout=0.5)
        ser.flushInput()
        ser.flushInput()
        time.sleep(2.5)
        log.debug(">>> strategy init")
        serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
        log.debug("<<< strategy init")
        proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
        proto.set_acknowledge(False)
        for i in range(20):
            print proto.send_string(35, "C123")
            time.sleep(0.1)

        self.assertEquals(pjon_protocol_constants.ACK, proto.send_string(35, "C123"))

    @skip
    def test_send_string__should_send_packet_with_ack_to_real_hardware(self):
        ser = serial.Serial('COM6', 115200, write_timeout=0.2, timeout=0.5)
        ser.flushInput()
        ser.flushInput()
        time.sleep(2.5)
        log.debug(">>> strategy init")
        serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
        log.debug("<<< strategy init")
        proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
        proto.set_acknowledge(True)

        '''
          #define MODE_BIT        1 // 1 - Shared | 0 - Local
          #define SENDER_INFO_BIT 2 // 1 - Sender device id + Sender bus id if shared | 0 - No info inclusion
          #define ACK_REQUEST_BIT 4 // 1 - Request synchronous acknowledge | 0 - Do not request acknowledge
        '''

        for i in range(30):
            print proto.send_string(35, "C123", packet_header=4)  # [0, 0, 1]: Local bus  | No sender info included | Acknowledge requested
            time.sleep(0.1)

        self.assertEquals(pjon_protocol_constants.ACK, proto.send_string(35, "C123", packet_header=4))




