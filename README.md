# Reclaim Your LG webOS TV

Rooted-TV privacy hardening and debloat for LG webOS: an **on-device telemetry
wall** (no router changes), a firewall that defeats the TV's DNS-evasion
tricks, telemetry daemon masking that survives reboots, and a reusable toolkit
of stdlib-only scripts. Everything here was built and verified end-to-end on a
real 2022 LG TV, then made generic.

Tested on: **LG UQ8050PSB (2022, India, "webOS 22" / internal 7.5.7 Lite
build)**. The approach applies to rooted webOS 5–9 TVs generally; paths and
behavior on "Lite" regional builds differ from guides written for standard
builds — the Gotchas section documents every difference we hit.

> **This is not a rooting guide.** Rooting itself is done by the excellent
> community tools linked below (we used
> [slopbro](https://github.com/throwaway96/slopbro); see also
> [webosbrew.org](https://webosbrew.org)). This project starts where rooting
> ends: **what to do with root** so the TV stops collecting and phoning home —
> while keeping the Content Store, app updates, Netflix/Prime/YouTube/etc.
> working.

---

## Why

LG smart TVs run Automatic Content Recognition (ACR) — a process that samples
what's on screen every few seconds (including HDMI inputs) and sends it to
LG and its data partners — plus ad beacons, remote loggers, crash/telemetry
upload pipelines, and pre-installed promo apps. Opt-out toggles exist, but
research ([arXiv 2409.06203](https://arxiv.org/html/2409.06203v1)) and the
2013 DoctorBeet incident show opt-outs don't reliably stop the traffic. So
this project doesn't trust settings: it **removes the collectors and walls off
the endpoints**, on the TV itself, with nothing deleted and everything
reversible.

## What you get

| Layer | What it does | File(s) |
|---|---|---|
| **Hosts wall** | ~315 LG telemetry/ad/ACR domains blackholed at boot | `hooks/55-lgblock`-style hook + `scripts/build_blocklist.py` + `blocklists/final_blocklist.example.txt` |
| **DNS firewall** | Drops all direct DNS except your chosen resolver (kills hardcoded-DNS evasion), kills encrypted DNS (DoT/DoQ :853), drops raw-IP LG endpoints | `hooks/40-lgfirewall.sh` |
| **Daemon masking** | Empty-file bind-mounts over ~15 telemetry binaries (sdx, acr2, admanager, rdxd, remotelogger, uploadd, voice pipeline, Live Plus…) so they can't execute or respawn | `hooks/30-lgmask.sh` + `hooks/masklist.txt` |
| **Preload kill** | Stops the TV force-loading YouTube/Netflix/Prime into RAM at boot | `hooks/fix-preload.sh` |
| **Toolkit** | Root-shell client, SSAP query client, IPK payload extractor, blocklist builder — all Python stdlib, zero dependencies | `tools/` |

Everything re-applies itself at every boot via Homebrew Channel init.d hooks,
and nothing on the read-only system is modified — masking is a bind-mount of
an empty file *over* a binary; the original file is untouched underneath.

## Requirements

- A **rooted** webOS TV (Homebrew Channel installed) — see
  [webosbrew.org](https://webosbrew.org) and
  [cani.rootmy.tv](https://cani.rootmy.tv) for methods and patch status
- A PC on the same network with Python 3.8+ (no pip installs needed), `ssh`,
  and `curl`
- **Do not** plan to install firmware updates afterwards — updates patch the
  rooting methods permanently. The included hooks also blackhole LG's update
  servers so updates can't install silently.

## The build, step by step

> Full procedures for rooting are upstream (slopbro/webosbrew docs). Steps 2+
> assume a root shell on the TV (root SSH or the Homebrew Channel telnet on
> port 23) and the PC able to reach the TV. Replace `192.168.1.50` with your
> TV's IP.

**1. Root the TV** with the method your firmware allows, then immediately
freeze updates: create the flag
`/var/luna/preferences/webosbrew_block_updates` (the Homebrew Channel's
"Block system updates" toggle does this) — its boot script blackholes
`snu/su/su-ssl/su-dev.lge.com`.

**2. Build and ship the blocklist**

```bash
python scripts/build_blocklist.py          # downloads sources, applies carve-outs
# copy final_blocklist.txt to the TV:
curl -T final_blocklist.txt "ftp://..."    # or serve it:
python -m http.server 8100                 # then on the TV:
#   curl http://<PC_IP>:8100/final_blocklist.txt -o /var/lib/webosbrew/lgblock.txt
```

**3. Install the boot hooks** (order matters — see Gotchas):

```bash
# on the TV, as root:
mkdir -p /var/lib/webosbrew/init.d
# upload hooks/55-lgblock, hooks/30-lgmask + masklist.txt, hooks/40-lgfirewall
# into /var/lib/webosbrew/init.d/  (names MUST contain no dots — run-parts!)
sh /var/lib/webosbrew/init.d/55-lgblock     # apply the wall now
sh /var/lib/webosbrew/init.d/30-lgmask      # mask + kill the daemons now
sh /var/lib/webosbrew/init.d/40-lgfirewall  # apply the firewall now
```

Edit `40-lgfirewall.sh` first: set your allowed DNS resolver(s) in the ACCEPT
lines (default: Cloudflare `1.1.1.1` / `1.0.0.1`). Then point the TV's DNS at
the same resolver (Settings → network → advanced → DNS, or as root:
`connmanctl config <service> --nameservers 1.1.1.1 1.0.0.1` — persistent).

**4. Kill the app preloads** (`hooks/fix-preload.sh`) — flips the persisted
`allowedApps` map in `/var/preferences/webos-preload-manager-conf.json` to
`false` for the usual suspects and closes resident copies.

**5. Verify** after a reboot:

```bash
ping -c1 lgsmartad.com        # → 127.0.0.1 (blocked)
ping -c1 in.lgtvsdp.com       # → real AWS IP (store still alive)
ps aux | grep -E 'sdx|acr2|admanager|rdxd|remotelogger|uploadd'   # → nothing
nslookup lgsmartad.com 8.8.8.8                                    # → fails (evasion dropped)
grep MemAvailable /proc/meminfo                                   # your RAM back
```

**6. Optional polish** (all third-party, all reversible):
[lucataco's debloat script](https://gist.github.com/lucataco/7c303b443934008a9031a55cfca552ec)
hides ~56 junk launcher tiles on this TV via LG's own regional block-list
(`/var/preferences/com.webos.applicationManager/blockedSystemAppList/IN.json`),
[Aerial Screensaver](https://github.com/aabytt/custom-screensaver-aerial)
replaces the screensaver with 330+ 4K aerial videos, and
[Glasshouse](https://github.com/rorygallagher2024/glasshouse) replaces the
whole home screen (explicit webOS 7 support, dashboard with remote-key
remapping).

## Gotchas we hit (so you don't have to)

These are the hard-won specifics of a 2022 **Lite** build:

1. **The TV's DNS proxy ignores `/etc/hosts`.** webOS runs connmand as a local
   stub resolver (`127.0.0.1:53`), and it does **not** consult the hosts file —
   it forwards upstream. So "redirect all DNS into the stub" designs feed
   evaders clean answers. The fix here: **drop every direct DNS egress** except
   the stub itself and your chosen resolver, so processes must use the
   hosts-filtered system resolver.
2. **`-m owner` doesn't exist** in this build's iptables — uid-based stub
   exclusions are impossible; destination-based ALLOWs are the workaround.
3. **`run-parts` silently skips hook files with dots in the name** — `foo.sh`
   never runs; `foo` does. And one correctly-named hook was *still* rejected
   until renamed (cause never identified — always `run-parts --test` your dir).
4. **Hook ordering matters.** Glasshouse's boot hook rebuilds `/etc/hosts`
   (keeping only lines it recognizes) — if your blocklist hook runs first, the
   wall is wiped at every boot. Our wall hook is named `55-*` so it runs last.
5. **Windows line endings are a silent killer.** A list file written in Python
   text mode on Windows carries `\r`; on-TV `while read` loops see paths like
   `/usr/sbin/sdx\r`, match nothing, and quietly do nothing. Always write/
   transfer in binary mode (the builder here does).
6. **Lite-build differences:** `/usr/sbin` is invisible to the `prisoner`
   (dev-mode) user; `appInstallService/dev/install` is a silent no-op over
   SSH; `opkg` has no writable destination. Installing IPKs as root = extract
   the `data.tar.*` from the ar archive and untar into
   `/media/cryptofs/apps/` (`tools/ipk_extract.py`).
7. **The boot window is real but gutted.** Some daemons (`voiceinput`) start
   at an earlier boot event than any writable hook can run, so a few seconds
   of exposure exist per boot — but their upload spools stay empty (checked),
   and every collector is masked/killed moments later.
8. **A broken-DNS window makes connmand sulk** (100% ICMP loss with a valid
   route). It self-heals or recovers on `systemctl restart connman`. Avoid
   DNS-breaking changes on a live TV.

## Transparency: blocked vs. kept

**Blocked (~315 domains):** telemetry pipeline (`rdx2.*`, `nextlgsdp` rdx
paths), the AI/LLM endpoints (`ngfts.lge.com` + clusters), ad delivery
(`lgsmartad.com` everywhere, `ad.lgappstv.com`, `lgads.tv`,
`adsmeasurement`), behavioral beacons (`cdpbeacon`, `nudge`, `recommend`,
`wiseconfig`, `rdl` on `lgtvcommon.com`), the ACR partner network
(`alphonso.tv`), LG Channels/promo/merchant spam, ThinQ/IoT (`lgthinq.com`,
`lgtviot.com`), firmware update servers, and raw-IP endpoints
(`156.147.69.32`, `54.186.247.229`). Plus ~15 binaries masked and 5 daemons'
preloads killed.

**Deliberately kept** (each because something measured broke without it):
`in.lgtvsdp.com` (store **and the TV clock** — blocking it breaks TLS
validation after cold boot), the `lgappstv.com` umbrella except its ad host,
`nsu.lge.com` (store search/installs die), India store APIs
(`in.lgeapi.com`, `in.nextlgsdp.com`), store CDN and artwork (`gfts` family),
and apex domains whose tracker subdomains are blocked individually instead.
The full generated list with every carve-out applied is
`blocklists/final_blocklist.example.txt`.

**Honest residuals:** DoH-over-443 is indistinguishable from streaming and
stays open; a seconds-wide boot window exists before hooks run (with empty
upload queues); the LG Content Store inherently sees store activity; and your
streaming apps' own telemetry belongs to those apps, not LG.

## Rollback

Nothing is deleted and nothing on the read-only rootfs changes, so:

- **One layer:** remove its hook file from `/var/lib/webosbrew/init.d/` and
  reboot; masks also clear per-binary with `umount <binary-path>`.
- **Everything:** delete the hook files + `/var/lib/webosbrew/lgblock.txt` +
  `masklist.txt`, reboot. A factory reset also reverts all of it (then
  **immediately** turn Auto Update off — reset restores LG's default ON, and
  one silent update can permanently close the rooting door).
- **Emergency:** `touch /var/luna/preferences/webosbrew_failsafe` makes the
  next boot skip Homebrew customizations.

## Credits & standing on shoulders

- [throwaway96](https://github.com/throwaway96) — slopbro, dejavuln-autoroot,
  faultmanager-autoroot, caniroot data
- [webosbrew](https://github.com/webosbrew) / [webosbrew.org](https://webosbrew.org)
  — Homebrew Channel, docs, ecosystem
- [Hagezi](https://github.com/hagezi/dns-blocklists) — LG webOS tracker list (CC BY 4.0)
- [furkan-bayrak/lg-tv-blocklist](https://github.com/furkan-bayrak/lg-tv-blocklist) —
  safe/strict tiers, the G1 audit carve-outs (CC BY 4.0)
- [lucataco's webos-debloat](https://gist.github.com/lucataco/7c303b443934008a9031a55cfca552ec) —
  tile hiding + preload approach
- [rorygallagher2024/glasshouse](https://github.com/rorygallagher2024/glasshouse),
  [aabytt/custom-screensaver-aerial](https://github.com/aabytt/custom-screensaver-aerial),
  [Simon34545/lginputhook](https://github.com/Simon34545/lginputhook) — polish layer

## License & disclaimer

MIT for everything in this repo (see `LICENSE`). The upstream lists this
project downloads are CC BY 4.0 — respect their terms. Smart TVs vary wildly
across regions and builds; **you** are responsible for what you run on your
hardware. Declining telemetry agreements may affect some convenience features
(voice control, ThinQ remote app). Never install firmware updates after
rooting unless you're ready to lose root permanently.
