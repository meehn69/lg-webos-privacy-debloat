#!/usr/bin/env python3
"""Minimal telnet (raw TCP) client for the TV's Homebrew Channel root shell.

Connects to the HBC telnet port, filters telnet negotiation bytes (IAC),
sends one command string, and prints everything the shell returns.

Usage: python tvshell.py <tv-ip> [port] <command...>   (port defaults to 23)
"""
import socket, sys, time, os


def read_until_quiet(sock, quiet_secs=3.0, max_secs=30):
    """Read from the socket until no new data arrives for quiet_secs."""
    sock.settimeout(quiet_secs)
    out = b""
    start = time.time()
    while time.time() - start < max_secs:
        try:
            chunk = sock.recv(65536)
            if not chunk:
                break
            out += chunk
            start = time.time()  # got data; restart the quiet window
        except socket.timeout:
            break
    return out


def strip_iac(data):
    """Remove telnet negotiation sequences (0xFF-prefixed triples)."""
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == 0xFF and i + 2 < len(data):
            cmd = data[i + 1]
            if cmd in (0xFB, 0xFC, 0xFD, 0xFE):  # WILL/WONT/DO/DONT: option byte follows
                i += 3
                continue
            i += 2
            continue
        out.append(b)
        i += 1
    return bytes(out)


def main():
    args = sys.argv[1:]
    host = args[0]
    port = int(args[1]) if args[1].isdigit() and len(args) > 2 else 23
    command = " ".join(args[2:] if args[1].isdigit() and len(args) > 2 else args[1:])
    marker = "===CMDDONE==="
    sock = socket.create_connection((host, port), timeout=10)
    quiet = float(os.environ.get("TVSHELL_QUIET", "3"))
    banner = read_until_quiet(sock, quiet_secs=quiet)
    text = strip_iac(banner).decode(errors="replace")
    if "login:" in text:
        sock.sendall(b"root\n")
        time.sleep(0.8)
        read_until_quiet(sock, quiet_secs=1.0)
    sock.sendall((command + "; echo " + marker + "\n").encode())
    result = read_until_quiet(sock)
    # Write raw bytes: console codepages can't represent all TV output
    sys.stdout.buffer.write(strip_iac(result).replace(marker.encode(), b"").strip() + b"\n")
    sock.close()


if __name__ == "__main__":
    main()
