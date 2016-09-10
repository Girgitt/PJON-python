import logging
import time
from unittest import TestCase, skip

import mock
import serial

from pjon_python.protocol import pjon_protocol, pjon_protocol_constants
from pjon_python.strategies import pjon_hwserial_strategy

try:
    xrange
except NameError:
    xrange = range


log = logging.getLogger("tests")


class TestPjonProtocol(TestCase):
    def setUp(self):
        self.rcvd_packets = []

    def print_args(*args, **kwargs):
        log.debug(">> print args")
        for arg in args:
            log.debug("arg: %s" % arg)
        try:
            for key, value in kwargs.iteritems():
                log.debug("kwarg: %s=%s" % (key, value))
        except AttributeError:
            for key, value in kwargs.items():
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

            timeout = 0.08
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

            timeout = 0.15
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
            ser.inWaiting.side_effect = [0, 1]

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
            ser.inWaiting.side_effect = [0]

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
            print(proto.send_string(35, "C123"))
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

        for i in range(20):
            print(proto.send_string(35, "C123", packet_header=4))  # [0, 0, 1]: Local bus  | No sender info included | Acknowledge requested
            time.sleep(0.1)

        self.assertEquals(pjon_protocol_constants.ACK, proto.send_string(35, "C123", packet_header=4))

    def test_get_header_from_internal_config__should_return_header_for_all_supported_internal_configurations(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)

            self.assertEquals(True, (proto.get_header_from_internal_config() & pjon_protocol_constants.ACK_REQUEST_BIT) >> proto.get_bit_index_by_value(
                pjon_protocol_constants.ACK_REQUEST_BIT))
            self.assertEquals(False, (proto.get_header_from_internal_config() & pjon_protocol_constants.SENDER_INFO_BIT) >> proto.get_bit_index_by_value(
                pjon_protocol_constants.SENDER_INFO_BIT))
            self.assertEquals(False, (proto.get_header_from_internal_config() & pjon_protocol_constants.MODE_BIT) >> proto.get_bit_index_by_value(
                pjon_protocol_constants.MODE_BIT))

            proto.set_sender_info(True)
            self.assertEquals(True, (
                proto.get_header_from_internal_config() & pjon_protocol_constants.SENDER_INFO_BIT) >> proto.get_bit_index_by_value(
                pjon_protocol_constants.SENDER_INFO_BIT))

            proto.set_shared_network(True)
            self.assertEquals(True, (
                proto.get_header_from_internal_config() & pjon_protocol_constants.MODE_BIT) >> proto.get_bit_index_by_value(
                pjon_protocol_constants.MODE_BIT))

    def test_get_overridden_header__should_overwrite_header_bits(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)

            self.assertEquals(0, proto.get_overridden_header(request_ack=False,
                                                             shared_network_mode=False,
                                                             include_sender_info=False))

            self.assertEquals(1, proto.get_overridden_header(request_ack=False,
                                                             shared_network_mode=True,
                                                             include_sender_info=False))

            self.assertEquals(2, proto.get_overridden_header(request_ack=False,
                                                             shared_network_mode=False,
                                                             include_sender_info=True))

            self.assertEquals(4, proto.get_overridden_header(request_ack=True,
                                                             shared_network_mode=False,
                                                             include_sender_info=False))

    def test_send__should_call_dispatch(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            with mock.patch('pjon_python.protocol.pjon_protocol.PjonProtocol.dispatch', create=True) as dispatch_mock:
                proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
                proto.send(1, 'test')
                self.assertEquals(1, dispatch_mock.call_count)

    def test_dispatch_should_put_new_outgoing_packet_to_outgoing_packets_buffer(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)

            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            self.assertEquals(0, proto.send(17, 'test'))

            self.assertEquals(1, len(proto.outgoing_packets))

            self.assertEquals(proto.outgoing_packets[-1].state, pjon_protocol_constants.TO_BE_SENT)
            self.assertEquals(proto.outgoing_packets[-1].content, 'test')
            self.assertEquals(proto.outgoing_packets[-1].device_id, 17)

    def test_dispatch_should_fail_on_too_many_outgoing_packets(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)

            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            for i in range(pjon_protocol_constants.MAX_PACKETS + 1):
                self.assertEquals(i, proto.send(i, 'test'))

            self.assertEquals(pjon_protocol_constants.FAIL, proto.send(1, 'test'))

    def test_update_should_send_new_packet(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)

            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            proto.set_acknowledge(False)

            serial_hw_strategy.can_start = mock.Mock()
            serial_hw_strategy.can_start.return_value = True

            self.assertEquals(0, proto.send(1, 'test0'))
            self.assertEquals(1, proto.send(2, 'test1'))
            self.assertEquals(2, proto.send(3, 'test2'))
            self.assertEquals(3, proto.send(4, 'test3'))
            self.assertEquals(4, proto.send(5, 'test4'))
            self.assertEquals(5, proto.send(6, 'test5'))
            self.assertEquals(6, proto.send(7, 'test6'))

            self.assertEquals(7, len(proto.outgoing_packets))
            proto.update()
            self.assertEquals(0, len(proto.outgoing_packets))

    def test_update_should_execute_error_handled_on_failed_max_attempts_send__and_delete_on_exceeded_max_attempts(self):
        with mock.patch('serial.Serial', create=True) as ser:
            serial_hw_strategy = pjon_hwserial_strategy.PJONserialStrategy(ser)
            single_packet = ['']
            multiple_packets = []
            pjon_protocol_constants.MAX_ATTEMPTS = 3
            packets_count = pjon_protocol_constants.MAX_ATTEMPTS + 1
            for i in xrange(packets_count):
                multiple_packets.extend(single_packet)

            self.assertEquals(packets_count * len(single_packet), len(multiple_packets))

            ser.read.side_effect = multiple_packets  # return values (empty) simulating no response to cause failure

            proto = pjon_protocol.PjonProtocol(1, strategy=serial_hw_strategy)
            proto.set_acknowledge(True)

            self.assertEquals(0, proto.send(1, 'test0'))
            self.assertEquals(1, proto.send(2, 'test1'))

            self.assertEquals(2, len(proto.outgoing_packets))
            with mock.patch('pjon_python.protocol.pjon_protocol.time', create=True) as time_mock:
                time_mock.time.side_effect = [time.time() + item for item in range(3 * pjon_protocol_constants.MAX_ATTEMPTS)]

                serial_hw_strategy.can_start = mock.Mock()
                serial_hw_strategy.can_start.return_value = True

                ser.inWaiting.return_value = 1  # needed for python 3.5

                for i in xrange(pjon_protocol_constants.MAX_ATTEMPTS):
                    proto.update()

                self.assertEquals(2, len(proto.outgoing_packets))

                error_function_mock = mock.Mock()
                proto.set_error(error_function_mock)
                proto.update()  # now failed outstanding packets should be deleted
                self.assertEquals(0, len(proto.outgoing_packets))

                error_function_mock.assert_any_call(pjon_protocol_constants.CONNECTION_LOST, 1)
                error_function_mock.assert_any_call(pjon_protocol_constants.CONNECTION_LOST, 2)
                self.assertEquals(2, error_function_mock.call_count)


