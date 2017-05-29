"""
todo:
1. put PJON-piper compiled binaries to
   /pjon_piper_bin/win
   /pjon_piper_bin/rpi

   OR maybe require setting PJON_PIPER_PATH ?

   solution: add binary (required path auto-discovery)
             but enable path overwriting

2. add "subprocess watchdog" to utils
3. add fakeredis client to utils
    or skip and use queues

3. inherit from base client in wrapper client
   - overload set sync/async
   - overload send
   - overload receive

   detect platform and launch proper client binary

   communicate with subprocess over fakeredis as done
    for supervisor_win
    OR through queues as already available in watchdog ?
"""
import os
import sys
import time
import logging
import subprocess

from threading import Thread
from pjon_python.base_client import PjonBaseSerialClient

log = logging.getLogger("pjon-cli")

"""
class PjonIoUpdateThread(Thread):
    def __init__(self, pjon_path):
        super(PjonIoUpdateThread, self).__init__()
        self._pjon_protocol = pjon_protocol

    def run(self):
        iter_cnt = 0
        while True:
            #if iter_cnt % 1 == 0:
            self._pjon_protocol.update()
            self._pjon_protocol.receive()
            #time.sleep(0.0008)
            iter_cnt += 1

"""


class ComPortUndefinedExc(Exception):
    pass


class ComPortNotAvailableExc(Exception):
    pass


class PjonPiperClient(object):
    def __init__(self, bus_addr=1, com_port=None, baud=115200):
        self._pipe = None
        self._bus_addr = bus_addr
        self._serial_baud = baud
        if sys.platform == 'win32':
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self._startupinfo.wShowWindow = subprocess.SW_HIDE
            self._pjon_piper_path = os.path.join(self.get_self_path(), 'pjon_piper_bin', 'win', 'PJON-piper.exe')
        else:
            raise NotImplementedError("platform not supported; currently provided support only for: win32")

        if com_port is None:
            raise ComPortUndefinedExc("serial port name is required")

        available_coms = self.get_coms()
        if com_port not in available_coms:
            raise ComPortNotAvailableExc("com port %s is not available in this system; available ports are: %s" % (com_port, str(available_coms)))

        # TODO:
            # 1. start pjon-piper in a watchdog thread and pass input/output queues
            # 2. implement send / receive methods
            # 3. implement periodic checks if com is available
            #   if not: restart watchdog (can be a permanent restart; no state machine required)
            # 4. implement polling or depend only pipes

    @staticmethod
    def get_self_path():
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def is_string_valid_com_port_name(com_name):
        try:
            if sys.platform == 'win32':
                if com_name.upper().startswith('COM'):
                    if not com_name.upper().endswith(' '):
                        if len(com_name) in (4, 5):
                            if 1 <= int(com_name.upper().split("COM")[-1]) <= 99:
                                log.debug("COM name matches expected form for Windows OS")
                                return True
                            else:
                                log.debug("com number outside 1-99")
                        else:
                            log.debug("wrong length: %s" % len(com_name))
                    else:
                        log.debug("ends with space")
                else:
                    log.debug("not starts with COM")
            else:
                raise NotImplementedError("platform not supported; currently provided support only for: win32")
        except ValueError:
            pass

        return False

    def get_coms(self):
        close_fds = False if sys.platform == 'win32' else True

        cmd_subprc_pipe = subprocess.Popen("%s coms" % self._pjon_piper_path, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)

        coms = []
        log.debug(">> cmd pipe out")
        while cmd_subprc_pipe:
            try:
                nex_tline = cmd_subprc_pipe.stdout.readline()
                if nex_tline == '':
                    break
                log.debug(nex_tline.strip())
                if self.is_string_valid_com_port_name(nex_tline.strip()):
                    log.debug("\_got a com port in the stdout")
                    coms.append(nex_tline.strip())
                else:
                    log.error("suspicious COM name in the output: %s" % nex_tline.strip())
            except AttributeError:
                pass
        log.debug("<< cmd pipe out")
        cmd_subprc_pipe.terminate()

        return coms


    """
    def start_client(self):
        if self._started:
            log.info('client already started')
            return
        io_thd = PjonIoUpdateThread(self._protocol)

        io_thd.setDaemon(True)

        io_thd.start()
    """



