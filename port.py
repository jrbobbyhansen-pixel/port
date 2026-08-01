#!/usr/bin/env python3
"""port — local port manager. List, check, and kill processes on ports."""

import argparse
import os
import re
import signal
import socket
import subprocess
import sys

__version__ = "1.0.0"


def get_listening_ports() -> list[dict]:
    """Return a list of dicts with pid, port, and process name for listening processes."""
    results = []
    try:
        if sys.platform == "darwin":
            output = subprocess.check_output(
                ["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"],
                stderr=subprocess.DEVNULL,
                timeout=10,
            ).decode("utf-8", errors="replace")
            for line in output.splitlines()[1:]:
                parts = line.split()
                if len(parts) < 9:
                    continue
                name = parts[0]
                pid = parts[1]
                addr_field = parts[-1] if parts[-1].startswith("*:") or ":" in parts[-1] else parts[-2]
                port_match = re.search(r":(\d+)$", addr_field)
                if port_match:
                    port = int(port_match.group(1))
                    results.append({"pid": pid, "port": port, "name": name})
        elif sys.platform == "linux":
            for proto in ("/proc/net/tcp", "/proc/net/tcp6"):
                if not os.path.exists(proto):
                    continue
                with open(proto) as f:
                    for line in f.readlines()[1:]:
                        parts = line.split()
                        if len(parts) < 10:
                            continue
                        local_addr = parts[1]
                        state = parts[3]
                        if state != "0A":
                            continue
                        port_hex = local_addr.split(":")[1]
                        port = int(port_hex, 16)
                        inode = parts[9]
                        pid = _pid_from_inode(inode)
                        name = _proc_name(pid) if pid else "?"
                        results.append({"pid": pid or "?", "port": port, "name": name})
        else:
            try:
                output = subprocess.check_output(
                    ["ss", "-tlnp"],
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                ).decode("utf-8", errors="replace")
                for line in output.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) < 4:
                        continue
                    addr = parts[3]
                    port_match = re.search(r":(\d+)$", addr)
                    if not port_match:
                        continue
                    port = int(port_match.group(1))
                    pid = "?"
                    name = "?"
                    if len(parts) >= 6:
                        proc_info = parts[6]
                        pid_match = re.search(r"pid=(\d+)", proc_info)
                        if pid_match:
                            pid = pid_match.group(1)
                        name_match = re.search(r'users:\(\("([^"]+)"', proc_info)
                        if name_match:
                            name = name_match.group(1)
                    results.append({"pid": pid, "port": port, "name": name})
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return results


def _pid_from_inode(inode: str) -> str | None:
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                fd_dir = f"/proc/{entry}/fd"
                if not os.access(fd_dir, os.R_OK):
                    continue
                for fd in os.listdir(fd_dir):
                    try:
                        link = os.readlink(f"{fd_dir}/{fd}")
                        if f"socket:[{inode}]" in link:
                            return entry
                    except (OSError, FileNotFoundError):
                        continue
            except PermissionError:
                continue
    except FileNotFoundError:
        pass
    return None


def _proc_name(pid: str) -> str:
    try:
        with open(f"/proc/{pid}/comm") as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return "?"


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def kill_port(port: int, signal_num: int = signal.SIGTERM) -> list[dict]:
    processes = get_listening_ports()
    killed = []
    for proc in processes:
        if proc["port"] == port and proc["pid"] != "?":
            try:
                os.kill(int(proc["pid"]), signal_num)
                killed.append(proc)
            except (ProcessLookupError, PermissionError, OSError) as e:
                killed.append({**proc, "error": str(e)})
    return killed


def cmd_list(args: argparse.Namespace) -> None:
    ports = get_listening_ports()
    if not ports:
        print("No listening ports found.")
        return
    ports.sort(key=lambda p: p["port"])
    print(f"{'PID':>8} {'PORT':>6} {'PROCESS'}")
    print("-" * 40)
    for p in ports:
        print(f"{p['pid']:>8} {p['port']:>6} {p['name']}")


def cmd_check(args: argparse.Namespace) -> None:
    in_use = is_port_in_use(args.port)
    if in_use:
        print(f"Port {args.port} is in use.")
        sys.exit(0)
    else:
        print(f"Port {args.port} is free.")
        sys.exit(1)


def cmd_kill(args: argparse.Namespace) -> None:
    sig = signal.SIGKILL if args.force else signal.SIGTERM
    killed = kill_port(args.port, sig)
    if not killed:
        print(f"No processes found on port {args.port}.")
        sys.exit(1)
    for proc in killed:
        if "error" in proc:
            print(f"Failed to kill PID {proc['pid']} ({proc['name']}): {proc['error']}")
        else:
            print(f"Killed PID {proc['pid']} ({proc['name']}) on port {proc['port']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="port",
        description="Local port manager — list, check, and kill processes on ports.",
    )
    parser.add_argument("--version", action="version", version=f"port {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all listening ports")

    check_parser = sub.add_parser("check", help="Check if a port is in use")
    check_parser.add_argument("port", type=int, help="Port number to check")

    kill_parser = sub.add_parser("kill", help="Kill processes on a port")
    kill_parser.add_argument("port", type=int, help="Port number to kill")
    kill_parser.add_argument("-f", "--force", action="store_true", help="Use SIGKILL instead of SIGTERM")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "kill":
        cmd_kill(args)


if __name__ == "__main__":
    main()
