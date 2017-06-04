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
import logging
import win32con
import win32api
import win32job
import threading
import subprocess

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


class PjonPiperClient(object):
    def __init__(self, bus_addr=1, com_port=None, baud=115200):
        self._pipe = None
        self._bus_addr = bus_addr
        self._serial_baud = baud
        self._piper_client_stdin_queue = Queue()
        self._piper_client_stdout_queue = Queue()

        if sys.platform == 'win32':
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self._startupinfo.wShowWindow = subprocess.SW_HIDE
            self._pjon_piper_path = os.path.join(self.get_self_path(), 'pjon_piper_bin', 'win', 'PJON-piper.exe')
        else:
            raise NotImplementedError("platform not supported; currently provided support only for: win32")

        self._pipier_client_subproc_cmd = "%s %s %s %s\n" % (self._pjon_piper_path, com_port.strip(), baud, bus_addr)

        if com_port is None:
            raise ComPortUndefinedExc("missing com_port kwarg: serial port name is required")

        available_coms = self.get_coms()
        if com_port not in available_coms:
            raise ComPortNotAvailableExc("com port %s is not available in this system; available ports are: %s" % (com_port, str(available_coms)))
        else:
            log.info("COM OK: %s" % com_port)

        self._pipier_client_watchdog = WatchDog(suproc_command=self._pipier_client_subproc_cmd,
                                                stdin_queue=self._piper_client_stdin_queue,
                                                stdout_queue=self._piper_client_stdout_queue)

        # TODO:
            # 1. start pjon-piper in a watchdog thread and pass input/output queues
            # 2. implement send / receive methods
            # 3. implement periodic checks if com is available
            #   if not: restart watchdog (can be a permanent restart; no state machine required)

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
                    pass
                    #log.debug("not starts with COM")
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

    def get_coms(self):
        close_fds = False if sys.platform == 'win32' else True

        cmd_subprc_pipe = subprocess.Popen("%s coms" % self._pjon_piper_path, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)

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

        return coms

    def get_pjon_piper_version(self):
        close_fds = False if sys.platform == 'win32' else True

        cmd_subprc_pipe = subprocess.Popen("%s version" % self._pjon_piper_path, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)

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
        return self._pipier_client_watchdog.start()

    def stop_client(self):
        return self._pipier_client_watchdog.stop()

    def send(self, device_id, payload):
        log.info("sending %s to %s" % (payload, device_id))
        self._piper_client_stdin_queue.put("send %s data=%s" % (device_id, payload))


class WatchDog(threading.Thread):
    TICK_SECONDS = .2
    START_SECONDS_DEFAULT = 2

    def __init__(self, suproc_command, stdin_queue, stdout_queue):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.setName('pjon_piper_thd')
        self._subproc_command = suproc_command
        self._birthtime = None
        self._stoped = False
        self._pipe = None
        self._stdout_queue = stdout_queue
        self._stdin_queue = stdin_queue
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
        self._pipe = subprocess.Popen(self._subproc_command, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)
        self._birthtime = time.time()

    def poll_on_subproc(self):
        close_fds = False if sys.platform == 'win32' else True
        try:
            while True:
                try:
                    if self._stoped:
                        self.log.log(1000, "killing within thread run")
                        self._pipe.terminate()
                        self._pipe = None
                        return True
                    else:

                        if self._pipe.poll() is not None:
                            if time.time() - self._birthtime < self.START_SECONDS_DEFAULT:
                                self.log.error('WatchDog(%r) start failed', self.getName())
                                self._stoped = True
                                self._pipe = None
                                return False
                            else:
                                self.log.error('WatchDog(%r) is dead, restarting', self.getName())
                                self._pipe = subprocess.Popen(self._subproc_command, shell=False, close_fds=close_fds, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, startupinfo=self._startupinfo, env=os.environ)
                                self._birthtime = time.time()
                        else:
                            try:
                                line = self._stdout_queue.get_nowait()
                                if len(line) > 1:
                                    #print line.strip()
                                    self.log.log(100, '%s: %s', self.getName(), line.strip())
                            except Empty:
                                pass
                    time.sleep(self.TICK_SECONDS)

                except Exception as e:
                    self.log.exception('WatchDog.run error: %r', e)
        finally:
            try:
                self._pipe.terminate()
            except AttributeError:
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

        return True

    def stop(self, skip_confirmation=False):
        try:
            self.log.info("PID to kill: %s" % self._pipe.pid)
            self._stoped = True

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
                self.log.log(2000, "attaching queue to stdout")
                while True:
                    try:
                        if self._stoped:
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
                    self.log.log(2000, "attaching queue to stdin")
                    while True:
                        try:
                            if self._stoped:
                                break
                            input_cmd = self._stdin_queue.get(timeout=.1)
                            if input_cmd == '':  # and self._pipe.poll() is not None:
                                continue
                            self._pipe.stdin.write(input_cmd+'\n')
                            self._pipe.stdin.flush()
                            continue
                        except Empty:
                            #self._pipe.stdin.write('\n')
                            #self._pipe.stdin.flush()
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
