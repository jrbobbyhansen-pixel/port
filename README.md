# port — local port manager

A zero-dependency CLI tool to list listening ports, check if a port is in use, and kill processes on a port. Works on macOS, Linux, and WSL using only the Python stdlib (`socket`, `os`, `subprocess`, `argparse`).

## Install

```bash
pip install git+https://github.com/jrbobbyhansen-pixel/port.git
# or just download port.py and run it directly:
curl -O https://raw.githubusercontent.com/jrbobbyhansen-pixel/port/main/port.py
chmod +x port.py
./port.py list
```

## Usage

```bash
# List all listening ports
port list

# Check if a port is in use (exit 0 = in use, exit 1 = free)
port check 8080

# Kill processes on a port (SIGTERM)
port kill 8080

# Force kill with SIGKILL
port kill 8080 --force
```
