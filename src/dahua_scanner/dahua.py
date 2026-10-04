import socket
import struct
import time
import logging
import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

LOGIN_TEMPLATE = b'\xa0\x00\x00\x60%b\x00\x00\x00%b%b%b%b\x04\x01\x00\x00\x00\x00\xa1\xaa%b&&%b\x00Random:%b\r\n\r\n'
GET_SERIAL = b'\xa4\x00\x00\x00\x00\x00\x00\x00\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
             b'\x00\x00\x00\x00\x00\x00\x00'
GET_CHANNELS = b'\xa8\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
               b'\x00\x00\x00\x00\x00\x00\x00\x00'
GET_SNAPSHOT = b'\x11\x00\x00\x00(\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
               b'\x00\x00\x00\n\x00\x00\x00%b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
               b'\x00\x00%b\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
JPEG_GARBAGE1 = b'\x0a%b\x00\x00\x0a\x00\x00\x00'
JPEG_GARBAGE2 = b'\xbc\x00\x00\x00\x00\x80\x00\x00%b'
TIMEOUT = 10

request_text_name = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getMachineName',
    'fields': {'name': 'machine_name'}
}
request_text_config = {
    'url' :'http://{}:{}/cgi-bin/configManager.cgi?action=getConfig&name=General',
    'fields': {'table.General.LocalNo': 'local_no', 'table.General.MachineAddress': 'address', 'table.General.MachineName': 'general_machine_name'}
}
request_snapshot = {
    'url': 'http://{}:{}/cgi-bin/snapshot.cgi?channel=1',
    'fields': {'snapshot': 'snapshot'}
}
request_type = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getDeviceType',
    'fields': {'type': 'type'}
}
request_serial = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getSerialNo',
    'fields': {'sn': 'serial_no'}
}
request_hardware = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getHardwareVersion',
    'fields': {'version': 'hw_version'}
}
request_software = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getSoftwareVersion',
    'fields': {'version': 'sw_version'}
}
request_builddate = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getBuildDate',
    'fields': {'builddate': 'build_date'}
}
request_system = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getSystemInfo',
    'fields': {'serialNumber': 'system_serial_no', 'deviceType': 'system_type', 'hardwareVersion': 'system_hw_version', 'processor': 'system_processor', 'appAutoStart': 'system_appstart'}
}
request_ptz_list = {
    'url': 'http://{}:{}/cgi-bin/ptz.cgi?action=getProtocolList',
    'fields': {'result': 'ptz'}
}
request_vendor = {
    'url': 'http://{}:{}/cgi-bin/magicBox.cgi?action=getVendor',
    'fields': {'vendor': 'vendor'}
}
request_interfaces = {
    'url': 'http://{}:{}/cgi-bin/netApp.cgi?action=getInterfaces',
    'fields': {'netInterface[0].Name': 'interface1', 'netInterface[0].Type': 'iftype1',
               'netInterface[1].Name': 'interface2', 'netInterface[1].Type': 'iftype2',
               'netInterface[2].Name': 'interface3', 'netInterface[2].Type': 'iftype3',
               'netInterface[3].Name': 'interface4', 'netInterface[3].Type': 'iftype4',}
}

HTTP_API_REQUESTS = [request_snapshot, request_text_name, request_vendor, request_text_config,request_type, request_serial, request_hardware, request_software, request_system, request_builddate, request_ptz_list, request_interfaces]

HTTP_PORTS = [80, 8080, 8000, 81, 8888, 88, 8081, 82, 83, 84, 9000, 8088, 8082, 8083, 8084, 9080, 9999]

DEVICE_CATEGORIES = {
    'DH-HAC-HUM': 'Pinhole',
    'DH-CA-UM': 'Pinhole',
    'DH-HAC-HDBW': 'Mobile',
    'DVR0404': 'ATM',
    'DHI-ITL': 'Traffic',
    'DH-MPTZ': 'Mobile PTZ',
    'DH-PVR': 'PVR',
    'UVSS': 'Vehicle',
    'UAV': 'Drone',
    'DH-M70': 'Multiservice Matrix',
    'ITC': 'Parking System',
    'DH-KVM0': 'KVM Switch',
    'DH-PFS': 'Managed Switch',
    'DH-KIT-HCVR': 'HD Surveillance System',
    'DH-TPC': 'Thermal',
    'DH-EVS': 'Video Storage',
    'ARC': 'Alarm System',
    'ARK': 'Access Control System',
    'ASM': 'Access Control Module',
    'VTH': 'Indoor Intercom',
    'VTN': 'Door Intercom',
    'VTO': 'Outdoor Intercom',
    'DHI-NVR4104': 'Wi-Fi NVR',
    'VTS': 'Home Operator',
    'DH-EPS': 'PTZ System',
    'DH-PTZ': 'PTZ System',
    'DH-SD': 'PTZ System',
    'DH-HAC': '1080p Camera',
    'DH-NKB': 'Keyboard',
    'DH-ESS': 'Storage',
    'DH-NVR': 'NVR',
    'DHI-NVR': 'NVR',
    'NVR': 'NVR',
    'DVR': 'DVR',
    'IPC': 'IP Camera',
}

logger = logging.getLogger("dahua")

class DahuaController:
    def __init__(self, ip, port, login, password, timeout: float = TIMEOUT):
        self.serial = ''
        self.channels_count = -1
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        try:
            self.socket.connect((ip, port))
            login_bytes = login.encode('ascii', errors='ignore')[:32]
            pass_bytes = password.encode('ascii', errors='ignore')[:32]
            pad_login = max(0, 8 - len(login_bytes)) * b'\x00'
            pad_pass = max(0, 8 - len(pass_bytes)) * b'\x00'
            length_byte = struct.pack('B', min(255, 24 + len(login_bytes) + len(pass_bytes)))

            self.socket.send(LOGIN_TEMPLATE % (length_byte, login_bytes,
                                               pad_login, pass_bytes,
                                               pad_pass, login_bytes,
                                               pass_bytes, str(int(time.time())).encode('ascii')))
            data = self.socket.recv(128)
            if len(data) >= 10:
                if data[8] == 1:
                    if data[9] == 4:
                        self.status = 2
                    else:
                        self.status = 1
                elif data[8] == 0:
                    self.status = 0
                else:
                    self.status = -1
            else:
                self.status = -1

            if self.status == 0:
                try:
                    self.socket.send(GET_SERIAL)
                    self.serial = self.receive_msg().split(b'\x00')[0].decode('ascii', errors='replace')
                    if not self.serial:
                        self.serial = '<unknown>'
                except Exception:
                    self.serial = '<unknown>'

                try:
                    self.get_channels_count()
                except Exception:
                    self.channels_count = 1
        except Exception:
            self.status = -1
            self.close()

    def close(self):
        if hasattr(self, 'socket') and self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_channels_count(self):
        self.socket.send(GET_CHANNELS)
        channels = self.receive_msg()
        self.channels_count = channels.count(b'&&') + 1
        return self.channels_count

    def receive_msg(self):
        header = self.socket.recv(32)
        if len(header) < 6:
            raise struct.error("Incomplete header")
        length = struct.unpack('<H', header[4:6])[0]
        data = b''
        while len(data) < length:
            chunk = self.socket.recv(min(length - len(data), 4096))
            if not chunk:
                break
            data += chunk
        return data

    def get_snapshot(self, channel_id):
        channel_id_bytes = struct.pack('B', channel_id)
        self.socket.send(GET_SNAPSHOT % (channel_id_bytes, channel_id_bytes))
        self.socket.settimeout(3)
        try:
            data = self.receive_msg_2(channel_id_bytes)
        finally:
            self.socket.settimeout(TIMEOUT)
        return data

    def receive_msg_2(self, c_id):
        garbage = JPEG_GARBAGE1 % c_id
        garbage2 = JPEG_GARBAGE2 % c_id
        data = b''
        i = 0
        while True:
            buf = self.socket.recv(1460)
            if not buf:
                break
            if i == 0:
                buf = buf[32:]
            data += buf
            if b'\xff\xd9' in data:
                break
            i += 1
        while garbage in data:
            t_start = data.find(garbage)
            t_end = t_start + len(garbage)
            t_start -= 24
            trash = data[t_start:t_end]
            data = data.replace(trash, b'')
        while garbage2 in data:
            t_start = data.find(garbage2)
            t_end = t_start + 32
            trash = data[t_start:t_end]
            data = data.replace(trash, b'')
        return data

    @staticmethod
    def dahua_http_check(req, ip, port, auth):
        url = req['url'].format(ip, port)
        logging.debug(auth)
        data = {}
        try:
            resp = requests.get(url,auth=auth,timeout=5)
        except Exception as e:
            logging.debug(e)
            pass
        else:
            if resp.status_code == 401:
                logging.debug(resp.headers)
                logging.debug('Got auth code by {}'.format(url))
                if not 'WWW-Authenticate' in resp.headers:
                    return False
                if 'Digest realm' in resp.headers['WWW-Authenticate']:
                    return {'http_port': port, 'auth': 'digest'}
                elif not 'Device_CGI' in resp.headers['WWW-Authenticate']:
                    # предполагаем, что в Basic везде такой вход
                    return False
                else:
                    return {'http_port': port, 'auth': 'basic'}
            if resp.status_code in [400, 404, 500]:
                logging.debug("{}: {}".format(port, resp.status_code))
            if resp.status_code == 200:
                logging.debug(resp.headers)
                if 'CONTENT-TYPE' in resp.headers and resp.headers['CONTENT-TYPE'] == 'image/jpeg':
                    data['snapshot'] = 'yes'
                    logging.debug('HTTP SCREENSHOT AVAILABLE')
                    return data
                else:
                    logging.debug("{}: {}".format(port, resp.text))
                    if not 'fields' in req:
                        return []
                    strs = resp.text.split('\n')
                    for key in req['fields']:
                        value = req['fields'][key]
                        found = False
                        for str in strs:
                            keyvalue = str.split('=')
                            if key==keyvalue[0]:
                                found = True
                                data[value] = keyvalue[1].strip()
                                logging.debug("{}: {}".format(req['fields'][key], keyvalue[1]))
                                break
                        if not found:
                            data[value] = '-'
                            logging.debug('{}: -'.format(req['fields'][key]))
                return data
        return False

    @staticmethod
    def get_extended_info(cam):
        logging.debug(cam)
        logging.debug('Try to get extended info  from cam {}'.format(cam['IP']))
        auth = HTTPBasicAuth(cam['Login'], cam['Password'])
        valid_port = None
        data = cam

        for port in HTTP_PORTS:
            check = DahuaController.dahua_http_check({'url': 'http://{}:{}/cgi-bin/'}, cam['IP'], port, None)
            if check and 'http_port' in check:
                valid_port = port
                data['http_port'] = port
                if check['auth'] == 'digest':
                    auth = HTTPDigestAuth(cam['Login'], cam['Password'])
                break

        if not valid_port:
            return False

        for req in HTTP_API_REQUESTS:
            res = DahuaController.dahua_http_check(req, cam['IP'], port, auth)
            if res and not 'http_port' in res:
                data.update(res)

        params = ""

        strcam_type = ', unknown'
        if not 'type' in data:
            data['type'] = 'unknown'
        elif data['type'].strip():
            strcam_type = ', %s' % data['type']

        if 'ptz' in data and data['ptz']:
            if 'DH-SD3' in data['ptz']:
                params += ", PTZ"

        if 'iftype2' in data and data['iftype2']:
            if 'Wireless' in data['iftype2']:
                params += ", Wi-Fi"

        type_array = {
            'DH-HAC-HUM': 'Pinhole',
            'DH-CA-UM': 'Pinhole',
            'DH-HAC-HDBW': 'Mobile',
            'DVR0404': 'ATM',
            'DHI-ITL': 'Traffic',
            'DH-MPTZ': 'Mobile PTZ',
            'DH-PVR': 'PVR',
            'UVSS': 'Vehicle',
            'UAV': 'Drone',
            'DH-M70': 'Multiservice Matrix',
            'ITC': 'Parking System',
            'DH-KVM0': 'KVM Switch',
            'DH-PFS': 'Managed Switch',
            'DH-KIT-HCVR': 'HD Surveillance System',
            'DH-TPC': 'Thermal',
            'DH-EVS': 'Video Storage',
            'ARC': 'Alarm System',
            'ARK': 'Access Control System',
            'ASM': 'Access Control Module',
            'VTH': 'Indoor',
            'VTN': 'Door',
            'VTO': 'Outdoor',
            'DHI-NVR4104': 'Wi-Fi NVR',
            'VTS': 'Home Operator',
            'DH-EPS': 'PTZ System',
            'DH-PTZ': 'PTZ System',
            'DH-SD': 'PTZ System',
            'DH-HAC': '1080p Storage/Camera',
            'DH-NKB': 'Keyboard',
            'DH-ESS': 'Storage',
            'DH-NVR0404FD': 'Forensic-NVR'
        }

        cam_summary = '%s:%s%s%s' % (cam['IP'], valid_port, strcam_type, params)
        logging.info('Found HTTP API: %s' % cam_summary)
        #if 'PTZ' in cam_summary or 'Wi-Fi' in cam_summary:
        #    post_str("%s\n%s:%s" % (cam_summary, cam['Login'], cam['Password']))
        return data

    @classmethod
    def get_device_category(cls, model_str: str) -> str:
        """Определяет категорию устройства по префиксу модели."""
        if not model_str:
            return ""
        for prefix, cat in DEVICE_CATEGORIES.items():
            if prefix in model_str:
                return cat
        return ""

    @classmethod
    def get_model(cls, ip: str, login: str, password: str, timeout: float = 2.0) -> str:
        """
        Быстро запрашивает модель камеры Dahua через HTTP CGI.
        Проверяет наиболее частые HTTP-порты, определяет auth (Digest/Basic)
        и возвращает название модели (например, 'DH-IPC-HFW4431R-Z (IP Camera)').
        """
        for port in HTTP_PORTS[:10]:
            try:
                with socket.create_connection((ip, port), timeout=0.5):
                    pass
            except (socket.timeout, OSError):
                continue

            try:
                url_type = f"http://{ip}:{port}/cgi-bin/magicBox.cgi?action=getDeviceType"
                with requests.Session() as session:
                    resp = session.get(url_type, timeout=timeout)
                    auth = None
                    if resp.status_code == 401:
                        hdr = resp.headers.get("WWW-Authenticate", "")
                        if "Digest" in hdr:
                            auth = HTTPDigestAuth(login, password)
                        else:
                            auth = HTTPBasicAuth(login, password)
                        resp = session.get(url_type, auth=auth, timeout=timeout)

                    model = ""
                    if resp.status_code == 200:
                        for line in resp.text.splitlines():
                            if line.startswith("type="):
                                model = line.split("=", 1)[1].strip()
                                break

                    if not model or model == "-":
                        url_sys = f"http://{ip}:{port}/cgi-bin/magicBox.cgi?action=getSystemInfo"
                        resp_sys = session.get(url_sys, auth=auth, timeout=timeout)
                        if resp_sys.status_code == 200:
                            for line in resp_sys.text.splitlines():
                                if line.startswith("deviceType="):
                                    model = line.split("=", 1)[1].strip()
                                    break

                    if model and model != "-":
                        category = cls.get_device_category(model)
                        return f"{model} ({category})" if category else model
            except Exception as e:
                logger.debug(f"HTTP model probe failed on {ip}:{port}: {e}")
                continue

        return ""