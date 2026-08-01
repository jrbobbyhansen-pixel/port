"""Tests for the port CLI tool."""

import subprocess
import sys
import socket
import time
import threading
import os
import random

PORT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "port.py")

# Add the project dir to path so we can import port module directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_port(*args: str) -> subprocess.CompletedProcess:
    """Run the port CLI with given args and return CompletedProcess."""
    return subprocess.run(
        [sys.executable, PORT_PATH, *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_version():
    result = run_port("--version")
    assert result.returncode == 0
    assert "port " in result.stdout


def test_list_help():
    result = run_port("list", "--help")
    assert result.returncode == 0
    assert "show this help message" in result.stdout


def test_check_help():
    result = run_port("check", "--help")
    assert result.returncode == 0
    assert "Port number to check" in result.stdout


def test_kill_help():
    result = run_port("kill", "--help")
    assert result.returncode == 0
    assert "Port number to kill" in result.stdout


def test_no_args_shows_help():
    result = run_port()
    assert result.returncode == 2
    assert "usage:" in result.stderr


def test_check_free_port():
    """Check a port that should be free (high ephemeral port)."""
    result = run_port("check", "59999")
    assert result.returncode == 1
    assert "is free" in result.stdout


def test_check_in_use_port():
    """Start a listener on a port, then check it."""
    port = random.randint(20000, 30000)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", port))
    server_socket.listen(1)
    try:
        result = run_port("check", str(port))
        assert result.returncode == 0
        assert "is in use" in result.stdout
    finally:
        server_socket.close()


def test_list_runs():
    """list should always run without error (may be empty in containers)."""
    result = run_port("list")
    assert result.returncode == 0
    # Should have header line
    assert "PID" in result.stdout
    assert "PORT" in result.stdout
    assert "PROCESS" in result.stdout


def test_kill_no_process():
    """Kill on a port with no process should exit 1."""
    result = run_port("kill", "59998")
    assert result.returncode == 1
    assert "No processes found" in result.stdout


def test_kill_force_flag():
    result = run_port("kill", "--help")
    assert "-f" in result.stdout or "--force" in result.stdout
    assert "SIGKILL" in result.stdout


def test_is_port_in_use_function():
    """Test the is_port_in_use function directly."""
    from port import is_port_in_use
    # A high ephemeral port should be free
    assert is_port_in_use(60000) is False


def test_get_listening_ports_function():
    """Test get_listening_ports returns a list."""
    from port import get_listening_ports
    ports = get_listening_ports()
    assert isinstance(ports, list)
    if ports:
        assert "pid" in ports[0]
        assert "port" in ports[0]
        assert "name" in ports[0]
