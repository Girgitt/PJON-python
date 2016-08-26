import pjon_protocol_constants
import crc8
import logging
import time
import random

log = logging.getLogger("pjon-prot")
'''
PROTOCOL SPEC:
PJON v4.2

    Transmission                                                 Response
     ____________________________________________________         _____
    | ID | LENGTH | HEADER |  SENDER ID  | CONTENT | CRC |       | ACK |
  <-|----|--------|--------|-------------|---------|-----|--> <--|-----|
    | 12 |   5    |  001   |    ID 11    |   64    |     |       |  6  |
    |____|________|________|_____________|_________|_____|       |_____|

  DEFAULT HEADER CONFIGURATION:
  [0, 1, 1]: Local bus | Sender info included | Acknowledge requested

  BUS CONFIGURATION:
  bus.set_acknowledge(true);
  bus.include_sender_info(true);
  _________________________________________________________________________________________

  Transmission
    ______________________________________
    | ID | LENGTH | HEADER | CONTENT | CRC |
  <-|----|--------|--------|---------|-----|-->
    | 12 |   5    |  000   |   64    |     |
    |____|________|________|_________|_____|

  HEADER CONFIGURATION:
  [0, 0, 0]: Local bus | Sender info included | Acknowledge requested

  BUS CONFIGURATION:
  bus.set_acknowledge(false);
  bus.include_sender_info(false);
  _________________________________________________________________________________________

  A Shared packet transmission example handled in HALF_DUPLEX mode, with acknowledge
  request, including the sender info:

  Channel analysis                         Transmission                                      Response
    _____         __________________________________________________________________         _____
   | C-A |       | ID | LENGTH | HEADER |    BUS ID   | BUS ID | ID | CONTENT | CRC |       | ACK |
 <-|-----|--< >--|----|--------|--------|-------------|--------|----|---------|-----|--> <--|-----|
   |  0  |       | 12 |   5    |  111   |     0001    |  0001  | 11 |   64    |     |       |  6  |
   |_____|       |____|________|________|_____________|________|____|_________|_____|       |_____|
                                        |Receiver info| Sender info |

'''


class PacketInfo(object):
    header = 0
    receiver_id = 0
    receiver_bus_id = [0, 0, 0, 0]
    sender_id = 0
    sender_bus_id = [0, 0, 0, 0]


class Packet(object):
    def __init__(self, payload, packet_length, packet_info):
        self._payload = payload
        self._packet_length = packet_length
        self._packet_info = packet_info
        self._receive_ts = None
        self._send_ts = None
        self._send_attempts_count = None

    @property
    def payload(self):
        return self._payload

    @property
    def packet_length(self):
        return self._packet_length

    @property
    def packet_info(self):
        return self._packet_info


class PjonProtocol(object):
    def __init__(self, device_id, strategy):
        self._acknowledge = True
        self._strategy = strategy
        self._device_id = device_id
        self._constanta = pjon_protocol_constants
        self._mode = pjon_protocol_constants.HALF_DUPLEX
        self._localhost = [0, 0, 0, 0]
        self._bus_id = [0, 0, 0, 0]
        self._router = False
        self._receiver_function = None
        self._store_packets = True
        self._stored_received_packets = []
        self._received_packets_buffer_length = 32
        # self._packet_template = ''.join(['%sender_id%', '%message_length%', '%end_mark%'])

    def begin(self):
        pass

    @staticmethod
    def compute_crc_8_for_byte(input_byte, crc):
        try:
            return crc8.AddToCRC(input_byte, crc)
        except TypeError:
            if type(input_byte) is str:
                if len(input_byte) == 1:
                    return crc8.AddToCRC(ord(input_byte), crc)
        raise TypeError("unsupported type for crc calculation; should be byte or str length==1")

    def receiver_function(self, new_ref):
        self._receiver_function = new_ref

    @property
    def bus_id(self):
        return self._bus_id

    @property
    def localhost(self):
        return self._localhost

    @property
    def device_id(self):
        return self._device_id

    @property
    def router(self):
        return self._router

    def set_router(self, val):
        if val:
            self._router = True
        self._router = False

    def set_receiver(self, receiver_function):
        self._receiver_function = receiver_function

    @property
    def shared(self):
        return False

    @property
    def mode(self):
        return self._mode

    @property
    def strategy(self):
        return self._strategy

    def bus_id_equality(self, id_1, id_2):
        '''not implemented'''
        return False

    def set_acknowledge(self, new_val):
        self._acknowledge = new_val

    @staticmethod
    def get_packet_info(packet):
        packet_info = PacketInfo()
        packet_info.receiver_id = packet[pjon_protocol_constants.RECEIVER_ID_BYTE_ORDER]
        packet_info.header = packet[pjon_protocol_constants.RECEIVER_HEADER_BYTE_ORDER]
        if packet_info.header & pjon_protocol_constants.MODE_BIT != 0:
            packet_info.receiver_bus_id = packet[pjon_protocol_constants.RECEIVER_BUS_ID_WITH_NET_INFO_BYTE_ORDER]
            if packet_info.header & pjon_protocol_constants.SENDER_INFO_BIT != 0:
                packet_info.sender_bus_id = 0 # packet + 7);
                packet_info.sender_id = packet[pjon_protocol_constants.SENDER_ID_WITH_NET_INFO_BYTE_ORDER]

        elif packet_info.header & pjon_protocol_constants.SENDER_INFO_BIT != 0:
            packet_info.sender_id = packet[pjon_protocol_constants.SENDER_ID_WITHOUT_NET_INFO_BYTE_ORDER]

        return packet_info

    def receive(self):
        data = [None for item in xrange(pjon_protocol_constants.PACKET_MAX_LENGTH)]
        state = 0
        packet_length = pjon_protocol_constants.PACKET_MAX_LENGTH
        CRC = 0
        shared = False
        includes_sender_info = False
        acknowledge_requested = False
        log.debug(">>> new packet assembly")
        for i in xrange(pjon_protocol_constants.PACKET_MAX_LENGTH):
            log.debug(" >> i: %s" % i)

            data[i] = state = self._strategy.receive_byte()
            if state == pjon_protocol_constants.FAIL:
                log.debug("  > returning fail - byte was not read")
                return pjon_protocol_constants.FAIL

            if i == 0 and data[i] != self._device_id and data[i] != pjon_protocol_constants.BROADCAST and not self.router:
                log.debug("  > returning busy; packet for someone else")
                return pjon_protocol_constants.BUSY

            if i == 1:
                if data[i] > 4 and data[i] < pjon_protocol_constants.PACKET_MAX_LENGTH:
                    packet_length = data[i]
                else:
                    log.debug("  > returning fail on wrong packet length")
                    return pjon_protocol_constants.FAIL

            if i == 2:   #  Packet header
                shared = data[2] & pjon_protocol_constants.MODE_BIT
                includes_sender_info = data[2] & pjon_protocol_constants.SENDER_INFO_BIT
                acknowledge_requested = data[2] & pjon_protocol_constants.ACK_REQUEST_BIT
                if(shared != self.shared) and not self.router:
                    log.debug("  > ret busy")
                    return pjon_protocol_constants.BUSY # Keep private and shared buses apart

            """
            If an id is assigned to this bus it means that is potentially
            sharing its medium, or the device could be connected in parallel
            with other buses. Bus id equality is checked to avoid collision
            i.e. id 1 bus 1, should not receive a message for id 1 bus 2.
            """
            '''
            if self.shared and shared and  not self.router and i > 2 and i < 7:
                if bus_id[i - 3] != data[i]:
                    return pjon_protocol_constants.BUSY
            '''
            if i == packet_length - 1:
                break
            CRC = self.compute_crc_8_for_byte(data[i], CRC)

        data = data[:packet_length]
        log.info(" >> packet: %s" % data)
        log.info(" >> calc CRC: %s" % CRC)

        if data[-1] == CRC:
            if acknowledge_requested and data[0] != pjon_protocol_constants.BROADCAST and self.mode != pjon_protocol_constants.SIMPLEX:
                if not self.shared or (self.shared and shared and self.bus_id_equality(data + 3, self.bus_id)):
                    self.strategy.send_response(pjon_protocol_constants.ACK)

            last_packet_info = self.get_packet_info(data)
            payload_offset = 3

            if shared:
                if includes_sender_info:
                    payload_offset += 9
                else:
                    payload_offset += 4
            else:
                if includes_sender_info:
                    payload_offset += 1
            payload = data[payload_offset:-1]

            log.info(" >> payload: %s" % payload)

            if self._receiver_function is not None:
                #                       payload, length,        packietInfo
                self._receiver_function(payload, packet_length, last_packet_info)

            if self._store_packets:
                packet_to_store = Packet(payload, packet_length, last_packet_info)
                self._stored_received_packets.append(packet_to_store)
                if len(self._stored_received_packets) > self._received_packets_buffer_length:
                    log.debug("truncating received packets")
                    self._stored_received_packets = self._stored_received_packets[
                                                    len(self._stored_received_packets) - self._received_packets_buffer_length:]

            return pjon_protocol_constants.ACK
        else:
            if acknowledge_requested and data[0] != pjon_protocol_constants.BROADCAST and self.mode != pjon_protocol_constants.SIMPLEX:
                if not self.shared and ( self.shared and shared and self.bus_id_equality(data + 3, self.bus_id)):
                    self.strategy.send_response(pjon_protocol_constants.NAK)
            return pjon_protocol_constants.NAK

    def send_string(self, recipient_id, string_to_send, string_length=None, packet_header=0):
        if string_length is None:
            log.debug("calculating str length")
            string_length = len(string_to_send)

        if string_to_send is None:
            log.debug("string is None; ret FAIL")
            return pjon_protocol_constants.FAIL

        if self.mode != pjon_protocol_constants.SIMPLEX and not self.strategy.can_start():
            log.debug("HALF_DUPLEX and BUSY: ret BUSY")
            return pjon_protocol_constants.BUSY

        CRC = 0

        # Transmit recipient device id
        self.strategy.send_byte(recipient_id)
        CRC = self.compute_crc_8_for_byte(recipient_id, CRC)

        # Transmit packet length
        self.strategy.send_byte(string_length + 4)
        CRC = self.compute_crc_8_for_byte(string_length + 4, CRC)

        # Transmit header header
        self.strategy.send_byte(packet_header)
        CRC = self.compute_crc_8_for_byte(packet_header, CRC)

        ''' If an id is assigned to the bus, the packet's content is prepended by
           the ricipient's bus id. This opens up the possibility to have more than
           one bus sharing the same medium. '''

        for i in xrange(string_length):
            self.strategy.send_byte(string_to_send[i])
            CRC = self.compute_crc_8_for_byte(string_to_send[i], CRC)

        self.strategy.send_byte(CRC)

        # FIXME: any reason why not take ack requirement from the header?
        if not self._acknowledge \
                or recipient_id == pjon_protocol_constants.BROADCAST \
                or self.mode == pjon_protocol_constants.SIMPLEX:
            log.debug("no ACK required; not BROADCAST; or SIMPLEX; ret ACK")
            return pjon_protocol_constants.ACK

        log.debug(">>> receiving response")
        response = self.strategy.receive_response()
        log.debug("<<< receiving response; received: %s" % response)

        if response == pjon_protocol_constants.ACK:
            log.debug("received ACK resp; ret ACK")
            return pjon_protocol_constants.ACK

        ''' Random delay if NAK, corrupted ACK/NAK or collision '''

        if response != pjon_protocol_constants.FAIL:
            log.debug("collision or corruption; sleeping")
            time.sleep( random.randint(0, pjon_protocol_constants.COLLISION_MAX_DELAY/1000))

            # FIXME: original PJON lib does not return anything
            return pjon_protocol_constants.BUSY

        if response == pjon_protocol_constants.NAK:
            return pjon_protocol_constants.NAK

        return pjon_protocol_constants.FAIL
