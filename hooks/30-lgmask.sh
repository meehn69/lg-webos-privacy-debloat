#!/bin/sh
# 30-lgmask.sh — Neutralize LG telemetry/ads/ACR/voice-upload binaries.
# Runs at every boot via HBC startup run-parts. Fully reversible: each entry
# is a bind-mount of an empty file over the binary (original file untouched
# on the read-only rootfs; `umount <path>` restores it).
#
# Masked (decided with user: voice pipeline + ThinQ connectivity killed too):
#   sdx                - primary telemetry pipeline
#   admanager          - ad fetch/beacon daemon
#   adoverlay-service  - on-screen ad overlay
#   rdxd               - crash/diagnostics report uploader
#   remotelogger       - remote logging upload
#   uploadd            - general file upload daemon
#   acr2               - Automatic Content Recognition (watches what plays,
#                        including HDMI inputs)
#   livepick/livepickfull + app binaries - Live Plus (ACR companion)
#   voiceinput/voiceconductor + voice app - voice data pipeline
# NOTE: "sam" intentionally NOT masked on this Lite build (unknown function).

MASK_SRC=/tmp/lgmask_empty
LIST=/var/lib/webosbrew/masklist.txt

touch "$MASK_SRC"

# Apply masks (skip if already mounted)
while read -r p; do
    [ -f "$p" ] || continue
    grep -qs " $p " /proc/mounts || mount --bind "$MASK_SRC" "$p"
done < "$LIST"

# Kill any surviving instances (respawn fails while masked)
for name in sdx admanager adoverlay-service rdxd remotelogger uploadd acr2 \
            livepick livepickfull voiceconductor voiceinput \
            com.webos.app.livepick com.webos.app.livepick-full \
            com.webos.app.voice remotelogger_test; do
    pkill -9 -f "/$name" 2>/dev/null
done

echo "mask: telemetry binaries neutralized"
