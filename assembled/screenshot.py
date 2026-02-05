import os
import time
import platform
from datetime import datetime

# mss is used for taking screenshots
import mss
import mss.tools

# The following imports are for detecting the active window and are OS-specific.
# A try-except block is used to handle cases where a library is not installed.
try:
    if platform.system() == "Windows":
        import win32gui
        import win32process
        import psutil
    elif platform.system() == "Linux":
        from Xlib import display
    elif platform.system() == "Darwin": # macOS
        from AppKit import NSWorkspace
except ImportError as e:
    print(f"A required library is not installed: {e}")
    print("Please install it using the instructions in requirements.txt")
    exit(1)


def get_active_window_info():
    """
    Gets information about the currently active window.
    Returns the application name and window title as a tuple.
    Handles different operating systems.
    """
    system = platform.system()
    try:
        if system == "Windows":
            hwnd = win32gui.GetForegroundWindow()
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
            app_name = psutil.Process(pid).name()
            window_title = win32gui.GetWindowText(hwnd)
            return (app_name, window_title)

        elif system == "Linux":
            d = display.Display()
            root = d.screen().root
            window_id = root.get_full_property(d.intern_atom('_NET_ACTIVE_WINDOW'), 0).value[0]
            active_window = d.create_resource(window_id)
            window_title = active_window.get_wm_name()
            # Getting the app name can be tricky, so we'll use the title for differentiation
            return (window_title, window_title)

        elif system == "Darwin": # macOS
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()
            app_name = active_app.get('NSApplicationName', 'Unknown')
            # Window title detection on macOS can be complex, so we'll focus on the app name
            return (app_name, app_name)
            
    except Exception as e:
        # This can happen if the window closes while we're querying it
        # Or if there's no active window (e.g., on a lock screen)
        # print(f"Could not get active window info: {e}")
        return (None, None)

    return ("Unknown", "Unknown")


def take_screenshot(output_dir="screenshots"):
    """
    Takes a screenshot of the entire screen and saves it to a specified directory.
    """
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Generate a unique filename using a timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = os.path.join(output_dir, f"screenshot_{timestamp}.png")

    # Use mss to capture the screen
    with mss.mss() as sct:
        # Correctly capture all monitors and save to the specified filename
        sct.shot(mon=-1, output=filename)

    print(f"Screenshot saved to {filename}")


def main():
    """
    Main loop to monitor window changes and take screenshots.
    """
    print("Starting activity screenshotter... Press Ctrl+C to stop.")
    last_window_info = None
    
    try:
        while True:
            current_window_info = get_active_window_info()

            # Check if the window information is valid and has changed
            if current_window_info[0] is not None and current_window_info != last_window_info:
                app_name, window_title = current_window_info
                print(f"\nNew active window detected:")
                print(f"  App: {app_name}")
                print(f"  Title: {window_title}")
                
                take_screenshot()
                
                last_window_info = current_window_info

            # Wait for a short period before checking again to reduce CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping the script. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

