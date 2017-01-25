import logging
import math
import random
import time

from pjon_python.protocol import pjon_protocol_constants
from pjon_python.utils import crc8

try:
    xrange
except NameError:
    xrange = range


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

    def __str__(self):
        return "%s -> %s" % (self.sender_id, self.receiver_id)


class ReceivedPacket(object):
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

    def __str__(self):
        return "%s [%s]" % (str(self._packet_info), self.payload)


class OutgoingPacket(object):
    def __init__(self):
        self.header = None
        self.content = None
        self.device_id = None
        self.sender_id = None
        self.length = None
        self.state = 0
        self.registration = None
        self.timing = None
        self.attempts = 0

    def __str__(self):
        return "registration: %s. device_id: %s, payload: %s, state: %s, attempts: %s" % (self.registration, self.device_id, self.content, self.state, self.attempts)


class PjonProtocol(object):
    def __init__(self, device_id, strategy):
        self._acknowledge = True
        self._sender_info = True
        self._router = False
        self._strategy = strategy
        self._device_id = device_id
        self._constanta = pjon_protocol_constants
        self._shared = False
        self._mode = pjon_protocol_constants.HALF_DUPLEX
        self._localhost = [0, 0, 0, 0]
        self._bus_id = [0, 0, 0, 0]
        self._receiver_function = self.dummy_receiver
        self._error_function = self.dummy_error
        self._store_packets = True
        self._stored_received_packets = []
        self._received_packets_buffer_length = 32
        self._bit_index_by_value = {
            1:  0,
            2:  1,
            4:  2,
            8:  3,
            16: 4,
            32: 5,
            64: 6
        }
        self.outgoing_packets = []
        self._auto_delete = True

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

    def set_error(self, error_function):
        self._error_function = error_function

    @property
    def shared(self):
        return self._shared

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

    def set_sender_info(self, new_val):
        self._sender_info = new_val

    def set_shared_network(self, new_val):
        self._shared = new_val

    @staticmethod
    def dummy_receiver(*args, **kwargs):
        pass

    @staticmethod
    def dummy_error(*args, **kwargs):
        pass

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

    def get_bit_index_by_value(self, bit_value):
        return self._bit_index_by_value[bit_value]

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
                log.debug("  > returning busy; packet for someone else [i: %s, sreceiver: %s target: %s]" % (i, self._device_id, data[i]))
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
            log.debug("CRC OK")
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
                packet_to_store = ReceivedPacket(payload, packet_length, last_packet_info)
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

    def send_string(self, recipient_id, string_to_send, sender_id=None, string_length=None, packet_header=None):
        log.debug("send_string to device: %s payload: %s header: %s" % (recipient_id, string_to_send, packet_header))
        if packet_header is None:
            log.warning("send_string: packed_header is None")
            packet_header = self.get_header_from_internal_config()

        if string_length is None:
            log.debug("calculating str length")
            string_length = len(string_to_send)

        if string_to_send is None:
            log.debug("string is None; ret FAIL")
            return pjon_protocol_constants.FAIL

        if self.mode != pjon_protocol_constants.SIMPLEX and not self.strategy.can_start():    #FIXME: mode does not chec
            log.debug("HALF_DUPLEX and BUSY: ret BUSY")
            return pjon_protocol_constants.BUSY

        includes_sender_info = packet_header & pjon_protocol_constants.SENDER_INFO_BIT

        CRC = 0

        # Transmit recipient device id
        self.strategy.send_byte(recipient_id)
        CRC = self.compute_crc_8_for_byte(recipient_id, CRC)

        packet_meta_size_bytes = 4
        if includes_sender_info:
            packet_meta_size_bytes += 1

        # Transmit packet length
        self.strategy.send_byte(string_length + packet_meta_size_bytes)
        CRC = self.compute_crc_8_for_byte(string_length + packet_meta_size_bytes, CRC)

        # Transmit header header
        self.strategy.send_byte(packet_header)
        CRC = self.compute_crc_8_for_byte(packet_header, CRC)

        ''' If an id is assigned to the bus, the packet's content is prepended by
           the ricipient's bus id. This opens up the possibility to have more than
           one bus sharing the same medium. '''

        # transmit sender id if included in header
        if includes_sender_info:
            self.strategy.send_byte(sender_id)
            CRC = self.compute_crc_8_for_byte(sender_id, CRC)

        for i in xrange(string_length):
            self.strategy.send_byte(string_to_send[i])
            CRC = self.compute_crc_8_for_byte(string_to_send[i], CRC)

        self.strategy.send_byte(CRC)

        if not (packet_header & pjon_protocol_constants.ACK_REQUEST_BIT > 0):
            log.debug("packet_header: %s" % packet_header)
            log.debug("no ACK required; ret ACK")
            return pjon_protocol_constants.ACK
        if (recipient_id == pjon_protocol_constants.BROADCAST):
            log.debug("BROADCAST; ret ACK")
            return pjon_protocol_constants.ACK
        if (self.mode == pjon_protocol_constants.SIMPLEX):
            log.debug("SIMPLEX; ret ACK")
            return pjon_protocol_constants.ACK

        log.debug(">>> receiving response")
        response = self.strategy.receive_response()
        log.info("<<< receiving response; received: %s" % response)

        if response == pjon_protocol_constants.ACK:
            log.debug("received ACK resp; ret ACK")
            return pjon_protocol_constants.ACK

        ''' Random delay if NAK, corrupted ACK/NAK or collision '''

        if response != pjon_protocol_constants.FAIL:
            log.debug("collision or corruption; sleeping")
            time.sleep(random.randint(0, pjon_protocol_constants.COLLISION_MAX_DELAY / 1000))

            # FIXME: original PJON lib does not return anything
            return pjon_protocol_constants.BUSY

        if response == pjon_protocol_constants.NAK:
            return pjon_protocol_constants.NAK

        return pjon_protocol_constants.FAIL

    def send(self, recipient_id, payload):
        return self.dispatch(recipient_id, payload)

    def dispatch(self, recipient_id, payload, header=None, target_net=None, timing=None, forced_sender_id=None):
        if header is None:
            log.debug("dispatch: getting header from internal config")
            header = self.get_header_from_internal_config()

        payload_length = len(payload)

        if payload_length >= pjon_protocol_constants.PACKET_MAX_LENGTH:
            log.error("payload too big")
            return pjon_protocol_constants.FAIL

        if timing is None:
            timing = 0

        if self.shared:
            raise NotImplementedError("operation on shared bus (multiple networks) not implemented")

        if len(self.outgoing_packets) <= pjon_protocol_constants.MAX_PACKETS:
            outgoing_packet = OutgoingPacket()
            outgoing_packet.header = header
            outgoing_packet.content = payload
            outgoing_packet.device_id = recipient_id
            if forced_sender_id is None:
                outgoing_packet.sender_id = self.device_id
            else:
                outgoing_packet.sender_id = forced_sender_id
            outgoing_packet.length = len(payload)
            outgoing_packet.state = pjon_protocol_constants.TO_BE_SENT
            outgoing_packet.registration = time.time()
            outgoing_packet.timing = timing
            outgoing_packet.attempts = 0
            log.debug("adding packet to the outgoing packets list: %s" % str(outgoing_packet))
            self.outgoing_packets.append(outgoing_packet)

            return len(self.outgoing_packets) - 1

        self._error_function(pjon_protocol_constants.PACKETS_BUFFER_FULL, pjon_protocol_constants.MAX_PACKETS)

        return pjon_protocol_constants.FAIL

    def get_header_from_internal_config(self):
        header = 0
        if self.shared:
            log.debug("header for shared bus")
            header |= pjon_protocol_constants.MODE_BIT
        if self._sender_info:
            log.debug("header with sender info")
            header |= pjon_protocol_constants.SENDER_INFO_BIT
        if self._acknowledge:
            log.debug("header requiring ACK")
            header |= pjon_protocol_constants.ACK_REQUEST_BIT

        return header

    def get_overridden_header(self, request_ack=True, include_sender_info=False, shared_network_mode=False):
        header = self.get_header_from_internal_config()

        if request_ack:
            header |= pjon_protocol_constants.ACK_REQUEST_BIT
        else:
            #header |= ~(0xFF & (1 << self.get_bit_index_by_value(pjon_protocol_constants.ACK_REQUEST_BIT)))
            header &= ~(1 << self.get_bit_index_by_value(pjon_protocol_constants.ACK_REQUEST_BIT))

        if include_sender_info:
            header |= pjon_protocol_constants.SENDER_INFO_BIT
        else:
            header &= ~(1 << self.get_bit_index_by_value(pjon_protocol_constants.SENDER_INFO_BIT))

        if shared_network_mode:
            header |= pjon_protocol_constants.MODE_BIT
        else:
            header &= ~(1 << self.get_bit_index_by_value(pjon_protocol_constants.MODE_BIT))

        return header

    def update(self):
        log.debug(">>> update")
        for outgoing_packet in self.outgoing_packets:
            log.debug(" >> processing packet: %s" % outgoing_packet)
            if outgoing_packet.state == 0:
                log.debug("  > continue on outgoing_packet.state == 0")
                continue

            if (time.time() - outgoing_packet.registration)*1000 >= \
                outgoing_packet.timing + math.pow(outgoing_packet.attempts, 3):
                log.debug("   sending packet with header: %s" % outgoing_packet.header)
                outgoing_packet.state = self.send_string(outgoing_packet.device_id,
                                                         outgoing_packet.content,
                                                         sender_id=outgoing_packet.sender_id,
                                                         packet_header=outgoing_packet.header)
                log.info("  > send_string returned: %s" % outgoing_packet.state)
            else:
                log.debug("  > continue on time.time() - registration > timing + pow(attempts, 3)")
                continue

        was_packet_deleted = True
        while was_packet_deleted:
            was_packet_deleted = False
            for outgoing_packet in self.outgoing_packets:
                if outgoing_packet.state == pjon_protocol_constants.ACK:
                    if not outgoing_packet.timing:
                        if self._auto_delete:
                            log.debug("  > deleting packet from outgoing buffer")
                            log.debug("  > buffer before deletion: %s" % str(self.outgoing_packets))
                            self.outgoing_packets[:] = [item for item in self.outgoing_packets if item is not outgoing_packet]
                            log.debug("  > buffer after deletion: %s" % str(self.outgoing_packets))
                            was_packet_deleted = True
                            break
                    else:
                        outgoing_packet.attempts = 0
                        outgoing_packet.registration = time.time()
                        outgoing_packet.state = pjon_protocol_constants.TO_BE_SENT

                if outgoing_packet.state == pjon_protocol_constants.FAIL:
                    outgoing_packet.attempts += 1
                    if outgoing_packet.attempts > pjon_protocol_constants.MAX_ATTEMPTS:
                        if outgoing_packet.content[0] == pjon_protocol_constants.ACQUIRE_ID:
                            # FIXME: not really understand why outgoing packets queue would ever get ID acquisition packet?
                            self._device_id = outgoing_packet.device_id
                            self.outgoing_packets[:] = [item for item in self.outgoing_packets if
                                                        item is not outgoing_packet]
                            log.debug("  > continue on ACQUIRE ID")
                            was_packet_deleted = True
                            break
                            #continue
                        else:
                            self._error_function(pjon_protocol_constants.CONNECTION_LOST,
                                                 outgoing_packet.device_id)

                        if not outgoing_packet.timing:
                            if self._auto_delete:
                                log.debug("  > auto deleting failed packet")
                                self.outgoing_packets[:] = [item for item in self.outgoing_packets if
                                                            item is not outgoing_packet]
                                was_packet_deleted = True
                                break
                        else:
                            outgoing_packet.attempts = 0
                            outgoing_packet.registration = time.time()
                            outgoing_packet.state = pjon_protocol_constants.TO_BE_SENT
                    #FIXME: original PJON is not re-scheduling failed packets for re-sending
                    # if delivery failed but attempts below maximum allowable count; fixed below
                    #else:
                    #    outgoing_packet.state = pjon_protocol_constants.TO_BE_SENT

        return len(self.outgoing_packets)
