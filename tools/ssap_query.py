#!/usr/bin/env python3
"""Minimal SSAP (webOS TV control protocol) client using stdlib only.

Queries a webOS TV over the SSAP WebSocket using an existing PRESHARED_KEY
client key (saved by slopbro as <tv-ip>.key). Prints the JSON payload of the
first response message.

Usage: python ssap_query.py <tv-ip> <client-key-file> <ssap-uri> [json-payload]
"""
import socket, ssl, base64, os, json, struct, sys


def connect(host):
    # Connect to the TV's SSAP port (3001 = WebSocket over TLS, self-signed cert)
    raw = socket.create_connection((host, 3001), timeout=10)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx.wrap_socket(raw)


def ws_handshake(sock, host):
    # Standard WebSocket client handshake; webOS ignores Origin, send a plausible one.
    # Returns bytes received beyond the handshake response (possibly the first
    # WebSocket frames, already in flight inside the same TLS record).
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET /ssap/v1 HTTP/1.1\r\nHost: %s:3001\r\nUpgrade: websocket\r\n"
           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\nOrigin: file:///var/lib/jailer/webapp/com.webos.app.firstuse/local/firstuse/index.html\r\n\r\n"
           % (host, key))
    sock.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = sock.recv(4096)
        if not chunk:
            raise SystemExit("handshake: connection closed")
        resp += chunk
    head, _, leftover = resp.partition(b"\r\n\r\n")
    status = head.split(b"\r\n")[0]
    if b"101" not in status:
        raise SystemExit("handshake failed: " + status.decode(errors="replace"))
    return leftover


def send_text(sock, obj):
    # Send one masked WebSocket text frame containing a JSON document
    data = json.dumps(obj).encode()
    mask = os.urandom(4)
    hdr = b"\x81"  # FIN + text opcode
    n = len(data)
    if n < 126:
        hdr += bytes([0x80 | n])
    elif n < 65536:
        hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
    sock.sendall(hdr + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))


class FrameReader:
    """Reads WebSocket frames from the socket, serving buffered leftovers first."""
    def __init__(self, sock, initial=b""):
        self.sock = sock
        self.pending = bytearray(initial)

    def _read(self, n):
        while len(self.pending) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("socket closed")
            self.pending.extend(chunk)
        out = bytes(self.pending[:n])
        del self.pending[:n]
        return out

    def recv_msg(self):
        buf = b""
        while True:
            h = self._read(2)
            opcode = h[0] & 0x0F
            masked = h[0] & 0x80
            ln = h[1] & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._read(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._read(8))[0]
            mk = self._read(4) if masked else None
            data = self._read(ln)
            if mk:
                data = bytes(b ^ mk[i % 4] for i, b in enumerate(data))
            if opcode == 9:  # ping: ignore (no pong needed for this short session)
                continue
            if opcode == 8:  # close
                return None
            if opcode in (1, 2, 0):
                buf += data
                if h[0] & 0x80:  # FIN bit: message complete
                    return buf.decode(errors="replace")


def main():
    host, keyfile, uri = sys.argv[1], sys.argv[2], sys.argv[3]
    payload = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
    sock = connect(host)
    leftover = ws_handshake(sock, host)
    reader = FrameReader(sock, leftover)
    client_key = open(keyfile).read().strip()
    send_text(sock, {"type": "register", "pairingType": "PRESHARED_KEY", "client-key": client_key})
    reg = reader.recv_msg()
    if reg is None:
        raise SystemExit("register: connection closed or no message")
    try:
        regj = json.loads(reg)
    except ValueError:
        raise SystemExit("register: non-JSON message: " + repr(reg[:300]))
    send_text(sock, {"type": "request", "uri": uri, "payload": payload})
    # Read messages until we get the response (skip unrelated pushes)
    for _ in range(5):
        msg = reader.recv_msg()
        if msg is None:
            break
        try:
            j = json.loads(msg)
        except ValueError:
            continue
        if j.get("type") == "response":
            print(json.dumps(j.get("payload", j), indent=1))
            return
    raise SystemExit("no response received")


if __name__ == "__main__":
    main()
