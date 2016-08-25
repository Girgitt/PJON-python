from unittest import TestCase, skip
from pjon_python import pjon_protocol
from pjon_python import pjon_hwserial_strategy
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




