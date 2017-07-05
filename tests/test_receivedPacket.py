from unittest import TestCase
from pjon_python.protocol.pjon_protocol import  ReceivedPacket


class TestReceivedPacket(TestCase):
    def setUp(self):
        self._rcv_packet = ReceivedPacket('ABC123', 6, None)

    def test_payload(self):
        self.assertEqual('ABC123', self._rcv_packet.payload)

    def test_payload_as_string(self):
        self.assertEqual('ABC123', self._rcv_packet.payload_as_string)

    def test_payload_as_chars(self):
        self.assertEqual(['A', 'B', 'C', '1', '2', '3'], self._rcv_packet.payload_as_chars)

    def test_payload_as_bytes(self):
        self.assertEqual([65, 66, 67, 49, 50, 51], self._rcv_packet.payload_as_bytes)

    def test_packet_length(self):
        self.assertEqual(6, self._rcv_packet.packet_length)

    def test_packet_info(self):
        self.assertEqual(None, self._rcv_packet.packet_info)
