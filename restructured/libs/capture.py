# -*- coding: utf-8 -*-
"""
capture.py - Cross-platform Screenshot Module

Provides screenshot functionality for Windows, Linux, and macOS.
Platform is specified as a parameter to allow cross-compilation.

Usage:
    from capture import take_screenshot, start_auto_capture, stop_auto_capture
    
    # single screenshot
    take_screenshot('lnx', folder='screenshots')
    
    # auto capture every 30 seconds
    start_auto_capture('lnx', interval=30, folder='screenshots')
    stop_auto_capture()
"""

import os
import threading
import time
from datetime import datetime

# try to import screenshot libraries
try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

# for mac specific
try:
    import subprocess
    HAS_SUBPROCESS = True
except ImportError:
    HAS_SUBPROCESS = False

# global for auto capture thread
_capture_thread = None
_capture_running = False


def take_screenshot_win(folder='screenshots', filename=None):
    """
    take screenshot on windows using PIL ImageGrab.
    
    args:
        folder: output folder path
        filename: custom filename (auto-generated if None)
    
    returns:
        filepath if success, None if failed
    """
    if not HAS_PIL:
        print("[!] PIL not available, install with: pip install pillow")
        return None
    
    try:
        os.makedirs(folder, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        filepath = os.path.join(folder, filename)
        
        # PIL ImageGrab works best on Windows
        screenshot = ImageGrab.grab()
        screenshot.save(filepath)
        
        return filepath
        
    except Exception as e:
        print(f"[ERROR] Screenshot failed: {e}")
        return None


def take_screenshot_lnx(folder='screenshots', filename=None):
    """
    take screenshot on linux using mss (or PIL fallback).
    
    args:
        folder: output folder path
        filename: custom filename (auto-generated if None)
    
    returns:
        filepath if success, None if failed
    """
    try:
        os.makedirs(folder, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        filepath = os.path.join(folder, filename)
        
        # prefer mss on linux (works without display manager issues)
        if HAS_MSS:
            with mss.mss() as sct:
                # mon=-1 captures all monitors, mon=1 for primary
                sct.shot(mon=-1, output=filepath)
            return filepath
        
        # fallback to PIL (may not work on all linux setups)
        elif HAS_PIL:
            screenshot = ImageGrab.grab()
            screenshot.save(filepath)
            return filepath
        
        else:
            print("[!] No screenshot library available")
            print("[!] Install with: pip install mss pillow")
            return None
        
    except Exception as e:
        print(f"[ERROR] Screenshot failed: {e}")
        return None


def take_screenshot_mac(folder='screenshots', filename=None):
    """
    take screenshot on macos using screencapture command or PIL.
    
    args:
        folder: output folder path
        filename: custom filename (auto-generated if None)
    
    returns:
        filepath if success, None if failed
    """
    try:
        os.makedirs(folder, exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        filepath = os.path.join(folder, filename)
        
        # method 1: use native screencapture command (best quality)
        if HAS_SUBPROCESS:
            try:
                # -x = no sound, -C = capture cursor
                result = subprocess.run(
                    ['screencapture', '-x', filepath],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0 and os.path.exists(filepath):
                    return filepath
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        # method 2: use PIL ImageGrab (requires pyobjc)
        if HAS_PIL:
            try:
                screenshot = ImageGrab.grab()
                screenshot.save(filepath)
                return filepath
            except Exception:
                pass
        
        # method 3: use mss
        if HAS_MSS:
            with mss.mss() as sct:
                sct.shot(mon=-1, output=filepath)
            return filepath
        
        print("[!] No screenshot method available")
        return None
        
    except Exception as e:
        print(f"[ERROR] Screenshot failed: {e}")
        return None


def take_screenshot(platform, folder='screenshots', filename=None):
    """
    take screenshot on specified platform.
    
    args:
        platform: 'win', 'lnx', or 'mac'
        folder: output folder path
        filename: custom filename (auto-generated if None)
    
    returns:
        filepath if success, None if failed
    """
    platform = platform.lower()
    
    if platform == 'win':
        return take_screenshot_win(folder, filename)
    elif platform == 'lnx':
        return take_screenshot_lnx(folder, filename)
    elif platform == 'mac':
        return take_screenshot_mac(folder, filename)
    else:
        print(f"[!] Unknown platform: {platform}")
        print("[!] Use 'win', 'lnx', or 'mac'")
        return None


def start_auto_capture(platform, interval=60, folder='screenshots', callback=None):
    """
    start automatic screenshot capture at specified interval.
    
    args:
        platform: 'win', 'lnx', or 'mac'
        interval: seconds between captures (default 60)
        folder: output folder path
        callback: optional function called with filepath after each capture
    
    returns:
        True if started, False if already running
    """
    global _capture_thread, _capture_running
    
    if _capture_running:
        print("[!] Auto capture already running")
        return False
    
    _capture_running = True
    
    def capture_loop():
        while _capture_running:
            filepath = take_screenshot(platform, folder)
            if filepath and callback:
                callback(filepath)
            time.sleep(interval)
    
    _capture_thread = threading.Thread(target=capture_loop, daemon=True)
    _capture_thread.start()
    
    print(f"[*] Auto capture started: every {interval}s to {folder}/")
    return True


def stop_auto_capture():
    """
    stop automatic screenshot capture.
    
    returns:
        True if stopped, False if wasn't running
    """
    global _capture_running
    
    if not _capture_running:
        print("[!] Auto capture not running")
        return False
    
    _capture_running = False
    print("[*] Auto capture stopped")
    return True


def is_auto_capture_running():
    """check if auto capture is currently running"""
    return _capture_running


def get_available_methods():
    """
    get available screenshot methods on current system.
    
    returns:
        dict with library availability
    """
    return {
        'PIL': HAS_PIL,
        'mss': HAS_MSS,
        'subprocess': HAS_SUBPROCESS
    }


# test if run directly
if __name__ == "__main__":
    import sys
    
    print("[*] Screenshot Module Test")
    print(f"[*] Available methods: {get_available_methods()}")
    
    # detect current platform
    if sys.platform.startswith('win'):
        platform = 'win'
    elif sys.platform.startswith('linux'):
        platform = 'lnx'
    elif sys.platform.startswith('darwin'):
        platform = 'mac'
    else:
        platform = 'lnx'
    
    print(f"[*] Detected platform: {platform}")
    print("[*] Taking test screenshot...")
    
    filepath = take_screenshot(platform, folder='screenshots')
    
    if filepath:
        print(f"[+] Screenshot saved: {filepath}")
    else:
        print("[-] Screenshot failed")
