#!/usr/bin/env python3
"""Extract the data.tar.* payload from a webOS .ipk (Debian 'ar' archive).

Usage: python ipk_extract.py <file.ipk> <outdir>
Writes <outdir>/data.tar.gz (or .xz/.bz2 depending on compression).
"""
import sys, os

def main():
    ipk, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    with open(ipk, "rb") as f:
        magic = f.read(8)
        if magic[:8] != b"!<arch>\n":
            raise SystemExit("not an ar archive: " + repr(magic))
        while True:
            hdr = f.read(60)
            if len(hdr) < 60:
                break
            name = hdr[0:16].decode().strip()
            size = int(hdr[48:58].decode().strip())
            payload = f.read(size)
            if name.startswith("data.tar"):
                out = os.path.join(outdir, name)
                with open(out, "wb") as o:
                    o.write(payload)
                print("extracted:", out, size, "bytes")
            # ar members are 2-byte aligned
            if size % 2:
                f.read(1)

if __name__ == "__main__":
    main()
