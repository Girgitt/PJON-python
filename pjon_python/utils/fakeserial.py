# fakeSerial.py
# PySerial functional mocks
import uuid
from pjon_python.utils.RedisConn import RedisConn
import logging
import random
import fakeredis

log = logging.getLogger("fakeredis")

fake_redis_cli = fakeredis.FakeStrictRedis()
instance_id = 0

class Serial:
    """ class which uses redis (or fakeredis) pub/sub to communicate with other serial
    mocks. It's purpose is to enable half-duplex communication testing without
    OS-level serial port emulators.
    """

    def __init__(self, port='COM1', baudrate=19200, transport=None,
                 timeout=1, write_timeout=1, bytesize=8, parity='N',
                 stopbits=1, xonxoff=0, rtscts=0):

        #self._uuid = uuid.uuid1(clock_seq=random.randint(0, 1000000))
        global instance_id
        instance_id += 1
        self._uuid = instance_id
        if transport is None:

            self.transport = RedisConn(fake_redis_cli,
                                       sub_channel='pjon-serial',
                                       pub_channel='pjon-serial',
                                       cli_id=self._uuid)
        else:
            self.transport = RedisConn(transport,
                                       sub_channel='pjon-serial',
                                       pub_channel='pjon-serial')

        self.transport.subscribe('pjon-serial')

        self.name = port
        self.port = port
        self.timeout = timeout
        self.parity = parity
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.xonxoff = xonxoff
        self.rtscts = rtscts
        self._isOpen = True
        self._data = []


    @property
    def closed(self):
        return not self.isOpen()

    def isOpen(self):
        return self._isOpen

    def open(self):
        self._isOpen = True

    def close(self):
        self._isOpen = False

    def write(self, string):
        message = dict()
        message['originator_uuid'] = self._uuid
        message['payload'] = string
        self.transport.publish(message)

    def update_input_queue(self):
        new_byte_data = True
        while new_byte_data:
            new_byte_data = self.transport.listen(rcv_timeout=0.0001)
            if new_byte_data:
                if new_byte_data['originator_uuid'] != self._uuid:
                    #log.debug("received bytes: %s" % new_byte_data['payload'])
                    self._data.extend(new_byte_data['payload'])

    def read(self, size=1):
        self.update_input_queue()
        s = self._data[0:size]
        self._data = self._data[size:]
        return s

    def inWaiting(self):
        self.update_input_queue()
        return len(self._data)

    def readline(self):
        raise NotImplementedError

    def flushInput(self):
        self.update_input_queue()
        self._data = []

    def flushOutput(self):
        self._data = []

    def __str__(self):
        return "Serial<id=0xa81c10, open=%s>( port='%s', baudrate=%d," \
               % (str(self.isOpen), self.port, self.baudrate) \
               + " bytesize=%d, parity='%s', stopbits=%d, xonxoff=%d, rtscts=%d)"\
               % (self.bytesize, self.parity, self.stopbits, self.xonxoff,
                   self.rtscts)
