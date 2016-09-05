import sys

if sys.version_info[0] == 3:
    import codecs


def calc_crc_for_byte_array(byte_array):
    crc = 0
    for b in byte_array:
        crc = AddToCRC(b, crc)
    return crc


def calc_crc_for_hex_string(incoming):
    # convert to bytearray
    if sys.version_info[0] == 3:
        hex_data = codecs.decode(incoming, "hex_codec")
    else:
        hex_data = incoming.decode("hex")
    msg = bytearray(hex_data)
    result = 0
    for i in msg:
        result = AddToCRC(i, result)
    return hex(result)


def AddToCRC(b, crc):
    """ computes crc iteratively by returning updated crc input"""
    if b < 0:
        b += 256
    for i in range(8):
        odd = ((b ^ crc) & 1) == 1
        crc >>= 1
        b >>= 1
        if odd:
            crc ^= 0x8C # this means crc ^= 140
    return crc


def check(incoming):
    """Returns True if CRC Outcome Is 0xx or 0x0"""
    result = calc_crc_for_hex_string(incoming)
    if result == "0x0" or result == "0x00":
        return True
    else:
        return False


def append(incoming):
    """Returns the Incoming message after appending it's CRC CheckSum"""
    result = calc_crc_for_hex_string(incoming).split('x')[1].zfill(2)
    return incoming + result
