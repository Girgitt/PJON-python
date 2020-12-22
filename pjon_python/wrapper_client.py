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
import psutil
import atexit
import logging
import platform
import threading
import subprocess
from pjon_python.protocol.pjon_protocol import PacketInfo
from pjon_python.protocol.pjon_protocol import ReceivedPacket

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

log = logging.getLogger("pjon-cli")
log.addHandler(logging.NullHandler())


class ComPortUndefinedExc(Exception):
    pass


class ComPortNotAvailableExc(Exception):
    pass


class PjonPiperClient(threading.Thread):
    def __init__(self, bus_addr=1, com_port=None, baud=115200):
        super(PjonPiperClient, self).__init__()
        self._pipe = None
        self._bus_addr = bus_addr
        self._serial_baud = baud
        self._piper_client_stdin_queue = Queue()
        self._piper_client_stdout_queue = Queue()
        self._receiver_function = self.dummy_receiver
        self._error_function = self.dummy_error
        self._last_watchdog_poll_ts = 0
        self._piper_stdout_watchdog_timeout = 0
        self._piper_stdout_last_received_ts = 0


        if sys.platform == 'win32':
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self._startupinfo.wShowWindow = subprocess.SW_HIDE
            self._pjon_piper_path = os.path.join(self.get_self_path(), 'pjon_piper_bin', 'win', 'PJON-piper.exe')
        elif sys.platform == 'linux2':
            #os.setpgrp()
            if(self.is_arm_platform()):
                if self.is_raspberry():
                    self._pjon_piper_path = os.path.join(self.get_self_path(), 'pjon_piper_bin', 'rpi',
                                                         'pjon_piper')
                    #print(self._pjon_piper_path)
                else:
                    NotImplementedError("On ARM only Linux on Raspberry is supported")
            elif (self.is_x86_platform()):
			    self._pjon_piper_path = os.path.join(self.get_self_path(), 'pjon_piper_bin', 'linux',
                                                         'pjon_piper')
            else:
                raise NotImplementedError("this version of Linux is not supported yet")
        else:
            raise NotImplementedError("platform not supported; currently provided support only for: win32")
        
        if sys.platform == 'win32':
            self._pipier_client_subproc_cmd = "%s %s %s %s\n" % (self._pjon_piper_path, com_port.strip(), baud, bus_addr)
        elif sys.platform == 'linux2':
            self._pipier_client_subproc_cmd = [self._pjon_piper_path, com_port.strip(), str(baud), str(bus_addr)]
        if com_port is None:
            raise ComPortUndefinedExc("missing com_port kwarg: serial port name is required")

        available_coms = self.get_coms()
        if com_port not in available_coms:
            raise ComPortNotAvailableExc("com port %s is not available in this system; available ports are: %s" % (com_port, str(available_coms)))
        else:
            log.info("COM OK: %s" % com_port)

        self._pipier_client_watchdog = WatchDog(suproc_command=self._pipier_client_subproc_cmd,
                                                stdin_queue=self._piper_client_stdin_queue,
                                                stdout_queue=self._piper_client_stdout_queue,
                                                parent = self)

        self._packets_processor = ReceivedPacketsProcessor(self)

        atexit.register(self.stop_client)

           # TODO:
            # 3. implement periodic checks if com is available
            #   if not: restart watchdog (can be a permanent restart; no state machine required)

    @staticmethod
    def is_raspberry():
        call_result = subprocess.Popen(['cat', '/sys/firmware/devicetree/base/model'], stdout=subprocess.PIPE)
        if call_result.stdout.readline().strip().lower().startswith('raspberry'):
            return True
        return False

    @staticmethod
    def is_arm_platform():
        return bool(sum([item.lower().startswith('armv') for item in platform.uname()]))
    
    @staticmethod
    def is_x86_platform():
        return bool(sum([item.lower().startswith('x86') for item in platform.uname()]))
		
    @staticmethod
    def get_self_path():
        if sys.platform == 'win32':
            return os.path.dirname(os.path.abspath(__file__))
        else:
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
            elif 'linux' in sys.platform:
                if '/dev/tty' in com_name:
                    return True
            else:
                raise NotImplementedError("platform not supported; currently provided support only for: win32")
        except ValueError:
            pass

        return False

    @staticmethod
    def is_string_valid_pjon_piper_version(version_str):
        if version_str.upper().startswith('VERSION:'):
            return True
        return False

    @staticmethod
    def dummy_receiver(*args, **kwargs):
        pass

    @staticmethod
    def dummy_error(*args, **kwargs):
        pass

    @property
    def is_piper_stdout_watchdog_enabled(self):
        if self._piper_stdout_watchdog_timeout > 0:
            return True
        return False

    def set_piper_stdout_watchdog(self, timeout_sec=3):
        self._piper_stdout_watchdog_timeout = timeout_sec

    def reset_piper_stdout_watchdog(self):
        self._piper_stdout_last_received_ts = time.time()

    def should_piper_stdout_watchdog_issue_restart(self):
        if time.time() - self._piper_stdout_last_received_ts > self._piper_stdout_watchdog_timeout:
            return True
        return False

    def set_receiver(self, receiver_function):
        self._receiver_function = receiver_function

    def set_error(self, error_function):
        self._error_function = error_function

    def get_coms(self):
        close_fds = False if sys.platform == 'win32' else True

        if sys.platform == 'win32':
            cmd_subprc_pipe = subprocess.Popen("%s coms" % self._pjon_piper_path, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)
        else:
            cmd_subprc_pipe = subprocess.Popen([self._pjon_piper_path, "coms"], shell=False, close_fds=close_fds,
                                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                               bufsize=0, env=os.environ)

        coms = []
        #log.debug(">> cmd pipe out")
        while cmd_subprc_pipe:
            try:
                nex_tline = cmd_subprc_pipe.stdout.readline()
                if nex_tline == '':
                    break
                #log.debug(nex_tline.strip())
                if self.is_string_valid_com_port_name(nex_tline.strip()):
                    #log.debug("\_got a com port in the stdout")
                    coms.append(nex_tline.strip())
                else:
                    pass
                    #log.error("suspicious COM name in the output: %s" % nex_tline.strip())
            except AttributeError:
                pass
        #log.debug("<< cmd pipe out")
        cmd_subprc_pipe.terminate()

        if coms == []:
            log.warn("PJON-piper returned no serial ports; falling back to pyserial to enumerate available serials")
            from serial.tools import list_ports
            if sys.platform == 'win32':
                coms = [item.device for item in list_ports.comports()]
            elif sys.platform == 'linux2':
                coms = [item[0] for item in list_ports.comports(include_links=True)]

        return coms

    def get_pjon_piper_version(self):
        close_fds = False if sys.platform == 'win32' else True

        if sys.platform == 'win32':
            cmd_subprc_pipe = subprocess.Popen("%s version" % self._pjon_piper_path, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)
        elif sys.platform == 'linux2':
            cmd_subprc_pipe = subprocess.Popen([self._pjon_piper_path, 'version'], shell=False, close_fds=close_fds,
                                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                               bufsize=0, startupinfo=self._startupinfo, env=os.environ)

        possible_version_output = "unknown"

        log.debug(">> cmd pipe out")
        while cmd_subprc_pipe:
            nex_tline = cmd_subprc_pipe.stdout.readline()
            if nex_tline == '':
                break
            possible_version_output = nex_tline.strip()
            if self.is_string_valid_pjon_piper_version(possible_version_output):
                possible_version_output = possible_version_output.split("VERSION:")[-1].strip()
        log.debug("<< cmd pipe out")
        cmd_subprc_pipe.terminate()

        return possible_version_output

    def start_client(self):
        self._pipier_client_watchdog.start()
        self._packets_processor.start()
        time.sleep(0.05)
        while True:
            if time.time() - self._pipier_client_watchdog._birthtime < self._pipier_client_watchdog.START_SECONDS_DEFAULT:
                if self._pipier_client_watchdog._start_failed:
                    raise Exception("client start failed; are you running as root? - needed to access serial port")
                elif self._pipier_client_watchdog._pipe.poll() is None:
                    break
        return True

    def stop_client(self):
        log.info("..stopping client: %s" % str(self))
        self._pipier_client_watchdog.stop()
        self._packets_processor.stop()
        try:
            self._pipier_client_watchdog.join()
        except RuntimeError:
            pass
        try:
            self._packets_processor.join()
        except RuntimeError:
            pass
        return True

    def send(self, device_id, payload):
        log.debug("sending %s to %s" % (payload, device_id))
        self._piper_client_stdin_queue.put("send %s data=%s" % (device_id, payload))

    def send_without_ack(self, device_id, payload):
        log.debug("sending %s to %s" % (payload, device_id))
        self._piper_client_stdin_queue.put("send_noack %s data=%s" % (device_id, payload))


class ReceivedPacketsProcessor(threading.Thread):
    def __init__(self, parent):
        super(ReceivedPacketsProcessor, self).__init__()
        self._parent = parent
        self.setDaemon(True)
        self._stopped = False
        self.name = "piper packets processor"

    def run(self):
        try:
            while True:
                try:
                    if self._parent._pipier_client_watchdog._start_failed:
                        log.error("PJON-piper client start failed; Check if you run as root - needed for serial port access")
                        self._parent.stop_client()
                        self.stop()

                    if self._stopped:
                        return

                    line = self._parent._piper_client_stdout_queue.get(block=False)

                    if len(line) > 1:
                        line = line.strip()
                        log.debug('%s: %s', self.getName(), line)
                        if self.is_text_line_received_packet_info(line):
                            log.debug('%s: %s', self.getName(), line)
                            try:
                                packet = self.get_packet_info_obj_for_packet_string(line)
                                if packet.packet_length == len(packet.payload):
                                    payload = packet.payload_as_string
                                    packet_length = packet.packet_length
                                    packet_info = packet.packet_info
                                    self._parent._receiver_function(payload, packet_length, packet_info)
                                else:
                                    log.error("incorrect payload length for rcv string %s" % line)

                                if self._parent.is_piper_stdout_watchdog_enabled:
                                    self._parent.reset_piper_stdout_watchdog()

                            except ValueError:
                                log.exception("could not process incoming paket str")
                            finally:
                                pass
                        elif self.is_text_line_received_error_info(line):
                            try:
                                error_code = self.get_from_error_string__code(line)
                                error_data = self.get_from_error_string__data(line)
                                self._parent._error_function(error_code, error_data)

                            except ValueError:
                                log.exception("could not process incoming paket str")
                            finally:
                                pass

                except Empty:
                    time.sleep(0.01)
                    continue

                except (IOError, AttributeError):
                    break
        except KeyboardInterrupt:
            pass

    def stop(self, skip_confirmation=False):
        self._stopped = True

    @staticmethod
    def is_text_line_received_error_info(text_line):
        if text_line.strip().startswith("#ERR"):
            return True
        return False

    @staticmethod
    def get_from_error_string__code(packet_string):
        return int(packet_string.split("code=")[-1].split(" ")[0])

    @staticmethod
    def get_from_error_string__data(packet_string):
        return int(packet_string.split("data=")[-1])

    @staticmethod
    def is_text_line_received_packet_info(text_line):
        if text_line.strip().startswith("#RCV"):
            return True
        return False

    @staticmethod
    def get_from_packet_string__snd_id(packet_string):
        return int(packet_string.split("snd_id=")[-1].split(" ")[0])

    @staticmethod
    def get_from_packet_string__snd_net(packet_string):
        net_str = packet_string.split("snd_net=")[-1].split(" ")[0]
        return [int(item) for item in net_str.split(".")]

    @staticmethod
    def get_from_packet_string__rcv_id(packet_string):
        return int(packet_string.split("rcv_id=")[-1].split(" ")[0])

    @staticmethod
    def get_from_packet_string__rcv_net(packet_string):
        net_str = packet_string.split("rcv_net=")[-1].split(" ")[0]
        return [int(item) for item in net_str.split(".")]

    @staticmethod
    def get_from_packet_string__data_len(packet_string):
        return int(packet_string.split("len=")[-1].split(" ")[0])

    @staticmethod
    def get_from_packet_string__data(packet_string):
        return packet_string.split("data=")[-1]

    def get_packet_info_obj_for_packet_string(self, packet_str):
        packet_info = PacketInfo()
        PacketInfo.receiver_id = self.get_from_packet_string__rcv_id(packet_str)
        PacketInfo.receiver_bus_id = self.get_from_packet_string__rcv_net(packet_str)
        PacketInfo.sender_id = self.get_from_packet_string__snd_id(packet_str)
        PacketInfo.sender_bus_id = self.get_from_packet_string__snd_net(packet_str)
        payload = self.get_from_packet_string__data(packet_str)
        length = self.get_from_packet_string__data_len(packet_str)

        return ReceivedPacket(payload=payload, packet_length=length, packet_info=packet_info)


class WatchDog(threading.Thread):
    TICK_SECONDS = .01
    START_SECONDS_DEFAULT = 2

    def __init__(self, suproc_command, stdin_queue, stdout_queue, parent):
        threading.Thread.__init__(self)
        self.setDaemon(False) # we want it to survive parent's death so it can detect innactivity and terminate subproccess
        self.setName('pjon_piper_thd')
        self._subproc_command = suproc_command
        self._birthtime = None
        self._stopped = False
        self._start_failed = False
        self._pipe = None
        self._stdout_queue = stdout_queue
        self._stdin_queue = stdin_queue
        self._parent = parent
        if sys.platform == 'win32':
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self._startupinfo.wShowWindow = subprocess.SW_HIDE

        self.log = logging.getLogger(self.name)
        self.log.handlers = []
        self.log.addHandler(logging.NullHandler())
        #self.log.propagate = False
        self.log.setLevel(logging.INFO)

    def start_subproc(self):
        close_fds = False if sys.platform == 'win32' else True
        if sys.platform == 'win32':
            self._pipe = subprocess.Popen(self._subproc_command, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)
        elif sys.platform == 'linux2':
            self._pipe = subprocess.Popen(self._subproc_command, shell=False, close_fds=close_fds,
                                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          bufsize=0, env=os.environ, preexec_fn=os.setpgrp)

        self._birthtime = time.time()

    def poll_on_subproc(self):
        close_fds = False if sys.platform == 'win32' else True
        try:
            while True:
                try:
                    if self._stopped:
                        self.log.debug("poll on subproc: killing within thread run")
                        self._pipe.terminate()
                        self._pipe = None
                        return True
                    else:

                        if self._pipe.poll() is not None:
                            if time.time() - self._birthtime < self.START_SECONDS_DEFAULT:
                                self.log.error('WatchDog(%r) start failed', self.getName())
                                self._stopped = True
                                self._pipe = None
                                self._start_failed = True
                                return False
                            elif not self._stopped:
                                self.log.error('WatchDog(%r) is dead, restarting', self.getName())
                                if sys.platform == 'win32':
                                    self._pipe = subprocess.Popen(self._subproc_command, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)
                                elif sys.platform == 'linux2':
                                    self._pipe = subprocess.Popen(self._subproc_command, shell=False,
                                                                  close_fds=close_fds, stdin=subprocess.PIPE,
                                                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                                  bufsize=0,
                                                                  env=os.environ)
                                self._birthtime = time.time()

                                if self._parent.is_piper_stdout_watchdog_enabled:
                                    self._parent.reset_piper_stdout_watchdog()
                        #else:
                        #    if time.time() - self._birthtime > self.START_SECONDS_DEFAULT:
                        #        if time.time() - self._parent._last_watchdog_poll_ts > 10:
                        #            log.critical("parent thread not active; quitting")
                        #            self._pipe.terminate()
                        #            break
                        #
                        #        else:
                        #            pass
                        #            #log.info("OK")
                    #self._parent._last_watchdog_poll_ts = time.time()

                    if self._parent.is_piper_stdout_watchdog_enabled:
                        if time.time() - self._birthtime > self.START_SECONDS_DEFAULT:
                            if self._parent.should_piper_stdout_watchdog_issue_restart():
                                log.warning("PJON-piper restart issued by stdout watchdog")
                                self._pipe.terminate()

                    time.sleep(self.TICK_SECONDS)

                except Exception as e:
                    self.log.exception('WatchDog.run error: %r', e)

        finally:
            try:
                self._pipe.terminate()
            except (AttributeError, OSError):
                pass
            try:
                psutil.Process(self._pipe.pid).kill()
            except:
                pass

    def start(self):
        self.start_subproc()

        run_thd = threading.Thread(target=self.poll_on_subproc)
        run_thd.daemon = True
        run_thd.start()

        stdout_thd = threading.Thread(target=self.attach_queue_to_stdout)
        stdout_thd.daemon = True
        stdout_thd.start()

        stdin_thd = threading.Thread(target=self.attach_queue_to_stdin)
        stdin_thd.daemon = True
        stdin_thd.start()

        #stdout_process_thd = threading.Thread(target=self.process_stdout_output)
        #stdout_process_thd.daemon = True
        #stdout_process_thd.start()

        return True

    def stop(self, skip_confirmation=False):
        try:
            #self.log.info("PID to kill: %s" % self._pipe.pid)
            self._stopped = True

            if skip_confirmation:
                return True

            timeout = self.START_SECONDS_DEFAULT
            while timeout > 0:
                if self._pipe is None:
                    return True
                else:
                    time.sleep(self.TICK_SECONDS)
                    timeout -= self.TICK_SECONDS
            return False

        except AttributeError:
            self.log.exception("could not stop thd")
            return False

    @staticmethod
    def stop_by_pid(pid):
        process = psutil.Process(pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def attach_queue_to_stdout(self):
        start_ts = time.time()
        while time.time() - start_ts < self.START_SECONDS_DEFAULT:
            if self._pipe is not None:
                self.log.debug("attaching queue to stdout")
                while True:
                    try:
                        if self._stopped:
                            break
                        if self._start_failed:
                            break
                        nextline = self._pipe.stdout.readline()
                        if nextline == '':# and self._pipe.poll() is not None:
                            continue
                        self._stdout_queue.put(nextline.strip())

                    except AttributeError:
                        self.log.exception("stdout queue broken")
                        break
                if self._pipe:
                    self._pipe.stdout.close()
            else:
                self.log.warning("pipe is None; can't attach queue to stdout")

            time.sleep(0.2)

    def attach_queue_to_stdin(self):
        start_ts = time.time()
        while time.time() - start_ts < self.START_SECONDS_DEFAULT:
            try:
                if self._pipe is not None:
                    self.log.debug("attaching queue to stdin")
                    while True:
                        try:
                            if self._stopped:
                                break
                            if self._start_failed:
                                break
                            input_cmd = self._stdin_queue.get(block=False)
                            if input_cmd == '':  # and self._pipe.poll() is not None:
                                continue
                            self._pipe.stdin.write(input_cmd+'\n')
                            self._pipe.stdin.flush()
                            continue
                        except Empty:
                            time.sleep(0.01)
                            continue
                        except (IOError, AttributeError):
                            break
                    if self._pipe:
                        self._pipe.stdin.close()
                else:
                    self.log.warning("pipe is None; can't attach queue to stdin")

                time.sleep(0.2)
            except KeyboardInterrupt:
                pass
