''' Communication modes '''
SIMPLEX = 150
HALF_DUPLEX = 151

''' Protocol symbols '''
ACK = 6
ACQUIRE_ID = 63
BUSY = 666
NAK = 21

''' Reserved addresses '''
BROADCAST = 0
NOT_ASSIGNED = 255

''' Internalconstants '''
FAIL = 0x100
TO_BE_SENT = 74

''' HEADER CONFIGURATION '''
''' Packet header bits '''
MODE_BIT = 1        # 1 - Shared | 0 - Local
SENDER_INFO_BIT = 2 # 1 - Sender device id + Sender bus id if shared | 0 - No info inclusion
ACK_REQUEST_BIT = 4 # 1 - Request synchronous acknowledge | 0 - Do not request acknowledge

''' Errors '''
CONNECTION_LOST = 101
PACKETS_BUFFER_FULL = 102
MEMORY_FULL = 103
CONTENT_TOO_LONG = 104
ID_ACQUISITION_FAIL = 105

''' Constraints '''
MAX_ATTEMPTS = 125

''' Packets buffer length '''
MAX_PACKETS = 10

''' Max packet length, higher if necessary( and you have free memory '''
PACKET_MAX_LENGTH = 50

''' Maximum id scan time(5 seconds) '''
MAX_ID_SCAN_TIME = 5000000


''' additional constants compared to PJON v4.2'''
RECEIVER_ID_BYTE_ORDER = 0
RECEIVER_HEADER_BYTE_ORDER = 2
SENDER_ID_WITH_NET_INFO_BYTE_ORDER = 11
RECEIVER_BUS_ID_WITH_NET_INFO_BYTE_ORDER = 3

SENDER_ID_WITHOUT_NET_INFO_BYTE_ORDER = 3