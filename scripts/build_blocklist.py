#!/usr/bin/env python3
"""Build a merged LG webOS TV blocklist with store-preserving carve-outs.

Downloads two maintained community sources, merges and dedupes them, then
removes every domain the LG Content Store / TV clock / app installs need on an
India-region TV. The result is one domain per line, ready to be turned into
/etc/hosts entries by hooks/55-lgblock (see hooks/ in this repo).

Sources:
  - Hagezi LG webOS native tracker list (~231 domains)
    https://github.com/hagezi/dns-blocklists  (CC BY 4.0)
  - lg-tv-blocklist safe + strict tiers
    https://github.com/furkan-bayrak/lg-tv-blocklist  (CC BY 4.0)

Usage:
  python build_blocklist.py [output_file]      # default: final_blocklist.txt

The output is written in binary mode with LF endings ON PURPOSE: webOS init
scripts silently no-op line loops when files carry Windows CR bytes.
"""
import re
import sys
import urllib.request

SOURCES = [
    # Hagezi's LG webOS native tracker list (domains only)
    "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/wildcard/native.lgwebos-onlydomains.txt",
    # lg-tv-blocklist, both tiers
    "https://raw.githubusercontent.com/furkan-bayrak/lg-tv-blocklist/main/lists/safe-domains.txt",
    "https://raw.githubusercontent.com/furkan-bayrak/lg-tv-blocklist/main/lists/strict-domains.txt",
]

# NEVER block these on an India-region TV that keeps using the LG Content
# Store. Each entry exists because something measured broke without it:
ALLOW = {
    # --- store + clock (the classic India trap) ---
    "in.lgtvsdp.com",       # India store platform AND the TV's time source:
                            # blocking it breaks TLS cert validation ("not
                            # yet valid") after a cold boot
    "in.lgeapi.com",        # India store API backend
    "in.nextlgsdp.com",     # next-gen store/billing zone
    "in.ibs.nextlgsdp.com",
    "a.lgappstv.com",       # store CDN
    "nsu.lge.com",          # blocking breaks store search + app installs
    "snsu.lge.com",         # store-adjacent (rooted-G1 audit carve-out)
    # --- apexes that shelter legitimate services; tracker subdomains are
    #     listed individually by the sources and stay blocked ---
    "lge.com",
    "lgtvcommon.com",       # e.g. service.lgtvcommon.com is store-adjacent
    "nextlgsdp.com",
    "lgsmartplatform.com",
    # --- documented false positives (lg-tv-blocklist recon) ---
    "am.lge.com",
    "ig.lge.com",
    # --- pure content CDN (store artwork); not telemetry ---
    "gfts.lge.com",
    "aic-gfts.lge.com",
    "eic-gfts.lge.com",
    "kic-gfts.lge.com",
    # --- store-adjacent hosts from the rooted-G1 audit ---
    "service.lgtvcommon.com",
    "aic.service.lgtvcommon.com",
    "eic.service.lgtvcommon.com",
    "kic.service.lgtvcommon.com",
    "lgeapi.com",
    "aic.lgeapi.com",
    "eic.lgeapi.com",
    "kic.lgeapi.com",
    "de.lgeapi.com",
    "ngfts.nextlgsdp.com",
}

# The lgappstv.com family IS the Content Store. Only its dedicated ad host
# may be blocked; everything else under the umbrella goes.
STORE_FAMILY = "lgappstv.com"
STORE_FAMILY_BLOCK_OK = {"ad.lgappstv.com"}


def fetch(url):
    """Download one source list as text."""
    req = urllib.request.Request(url, headers={"User-Agent": "lg-webos-privacy-debloat/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def normalize(line):
    """Reduce one list line to a bare domain, or None if it isn't one."""
    d = line.strip().lower()
    if not d or d.startswith("#"):
        return None
    d = re.sub(r"^\*\.", "", d)                      # wildcard prefix
    d = re.sub(r"^(0\.0\.0\.0|127\.0\.0\.1)\s+", "", d).strip()  # hosts prefix
    if not d or "/" in d or " " in d:
        return None
    if not re.match(r"^[a-z0-9_.-]+$", d):
        return None
    return d


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "final_blocklist.txt"
    domains = {}
    for url in SOURCES:
        print(f"fetching {url}")
        for line in fetch(url).splitlines():
            d = normalize(line)
            if d:
                domains.setdefault(d, set()).add(url.rsplit("/", 1)[-1])

    # Carve-outs, with a report of everything that was rescued
    for d in sorted(d for d in domains if d in ALLOW):
        print(f"carve-out (removed): {d}")
        del domains[d]
    for d in sorted(domains):
        if d == STORE_FAMILY or d.endswith("." + STORE_FAMILY):
            if d not in STORE_FAMILY_BLOCK_OK:
                print(f"carve-out (store family): {d}")
                del domains[d]

    final = sorted(domains)
    # 'wb' + '\n': never let Windows text mode introduce CR bytes — webOS
    # init.d line loops silently skip lines ending in \r.
    with open(out_path, "wb") as f:
        f.write(("\n".join(final) + "\n").encode("ascii"))
    print(f"wrote {len(final)} domains to {out_path}")
    for check in ("nsu.lge.com", "in.lgtvsdp.com", "lgappstv.com"):
        print(f"safety check, {check} blocked: {check in domains}")


if __name__ == "__main__":
    main()
