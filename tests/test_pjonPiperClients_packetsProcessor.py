from unittest import TestCase
from pjon_python.wrapper_client import ReceivedPacketsProcessor
from pjon_python.wrapper_client import PjonPiperClient
import mock


class TestPipierClientPacketsProcessor(TestCase):
    def setUp(self):
        self.valid_packet_str = "rcvd snd_id=44 snd_net=204.204.204.204 rcv_id=45 rcv_net=205.205.205.205 id=0 hdr=6 pckt_cnt=38 len=8 data=ABC test"
        with mock.patch('pjon_python.wrapper_client.PjonPiperClient.get_coms', create=True) as get_coms_mock:
            get_coms_mock.return_value=["test"]
            with mock.patch('pjon_python.wrapper_client.PjonPiperClient.Watchdog', create=True) as watchdog_mock:
                self._rcvd_packets_processor = ReceivedPacketsProcessor(PjonPiperClient(com_port="test"))

    def test__is_text_line_received_packet_info__should_detect_rcvd_lines(self):

        self.assertFalse(self._rcvd_packets_processor.is_text_line_received_packet_info(" "))
        self.assertFalse(self._rcvd_packets_processor.is_text_line_received_packet_info("received something"))

        self.assertTrue(self._rcvd_packets_processor.is_text_line_received_packet_info("rcvd something"))

    def test_get_from_packet_string__snd_id(self):
        self.assertEqual(44, self._rcvd_packets_processor.get_from_packet_string__snd_id(self.valid_packet_str))

    def test_get_from_packet_string__snd_net(self):
        self.assertEqual([204, 204, 204, 204], self._rcvd_packets_processor.get_from_packet_string__snd_net(self.valid_packet_str))

    def test_get_from_packet_string__rcv_id(self):
        self.assertEqual(45, self._rcvd_packets_processor.get_from_packet_string__rcv_id(self.valid_packet_str))

    def test_get_from_packet_string__rcv_net(self):
        self.assertEqual([205, 205, 205, 205], self._rcvd_packets_processor.get_from_packet_string__rcv_net(self.valid_packet_str))

    def test_get_from_packet_string__data_len(self):
        self.assertEqual(8, self._rcvd_packets_processor.get_from_packet_string__data_len(self.valid_packet_str))

    def test_get_from_packet_string__data(self):
        self.assertEqual('ABC test', self._rcvd_packets_processor.get_from_packet_string__data(self.valid_packet_str))

    def test_get_packet_info_obj_for_packet_string__should_convert_packet_string(self):
        packet = self._rcvd_packets_processor.get_packet_info_obj_for_packet_string(self.valid_packet_str)
        self.assertNotEquals(None, packet)
        self.assertEqual(44, packet.packet_info.sender_id)
        self.assertEqual(45, packet.packet_info.receiver_id)
        self.assertEqual([205, 205, 205, 205], packet.packet_info.receiver_bus_id)
        self.assertEqual([204, 204, 204, 204], packet.packet_info.sender_bus_id)
        self.assertEqual('ABC test', packet.payload)
        self.assertEqual('ABC test', packet.payload_as_string)
        self.assertEqual(['A', 'B', 'C', ' ', 't', 'e', 's', 't'], packet.payload_as_chars)
        self.assertEqual([65, 66, 67, 32, 116, 101, 115, 116], packet.payload_as_bytes)
