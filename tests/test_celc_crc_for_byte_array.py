from unittest import TestCase
from pjon_python import crc8


class TestCelc_crc_for_byte_array(TestCase):
    def test_celc_crc_for_byte_array(self):
        self.assertEquals(106, crc8.calc_crc_for_byte_array([1, 21, 2, 45, 49, 97, 50, 115, 51, 100, 52, 102, 53, 103, 54, 104, 55, 106, 56, 107]))
        self.assertEquals(198, crc8.calc_crc_for_byte_array([1, 8, 2, 45, 65, 66, 67]))
        self.assertEquals(71, crc8.calc_crc_for_byte_array([1, 9, 2, 45, 65, 65, 65, 65]))
