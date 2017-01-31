from unittest import TestCase
from pjon_python.base_client import PjonBaseSerialClient
import platform
from unittest2.compatibility import wraps
import time

def skip_if_condition(condition, reason):
    def deco(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if condition:
                self.skipTest(reason)
            else:
                f(self, *args, **kwargs)
        return wrapper
    return deco


class TestSerial2pjonProxy(TestCase):
    def setUp(self):
        if platform.platform().find('armv') < 0:
            return
        self.cli = PjonBaseSerialClient(1, '/dev/ttyUSB1', write_timeout=0.005, timeout=0.005)
        self.cli.set_error(self.test_error_handler)
        self.cli.start_client()


    def test_error_handler(self, error_code=0, parameter=0):
        error_text = "code: %s, parameter: %s" % (error_code, parameter)
        if error_code == 101:
            error_text = "connection lost to node: %s" % parameter
        elif error_code == 101:
            error_text = "outgoing buffer full"

        if error_code > 0:
            self.fail(error_text)

    @skip_if_condition(platform.platform().find('armv') < 0, 'skipping on non-ARM as it is in-hardware test')
    def test_proxy_should_respond(self):
        time.sleep(5)
        for i in range(2):
            #self.cli.send_without_ack(35, 'C12345')
            self.cli.send(35, 'C12345')
            time.sleep(1)
        time.sleep(2)
