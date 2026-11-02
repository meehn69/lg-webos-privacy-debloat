#!/bin/sh
# 40-lgfirewall.sh — DNS egress allowlist + raw-IP endpoint drops. v3
# Runs at every boot via HBC startup run-parts (/var/lib/webosbrew/init.d).
#
# Policy (v3 — TV DNS moved to Cloudflare):
#  - Queries to the local DNS proxy (127.0.0.1 / ::1) are allowed.
#  - Queries to Cloudflare (1.1.1.1 / 1.0.0.1) are allowed — the TV's only
#    upstream resolvers, set via connmanctl (persistent).
#  - EVERY other direct DNS attempt is DROPPED, including the router's DNS
#    (this closes the router-DNS crack) and ISP/IPv6 RDNSS paths.
#  - Encrypted DNS (DoT/DoQ, port 853) is dropped entirely.
#  - Known raw-IP LG endpoints (hosts-file-immune) are dropped.
#  NOTE: -m owner is unavailable in this iptables build; destination allows
#  are the working substitute for a stub-UID exclusion.

IPT=/usr/sbin/iptables
IP6T=/usr/sbin/ip6tables

for PROTO in udp tcp; do
    # IPv4: local proxy + Cloudflare only
    $IPT -C OUTPUT -p $PROTO --dport 53 -d 127.0.0.1 -j ACCEPT 2>/dev/null || \
        $IPT -A OUTPUT -p $PROTO --dport 53 -d 127.0.0.1 -j ACCEPT
    $IPT -C OUTPUT -p $PROTO --dport 53 -d 1.1.1.1 -j ACCEPT 2>/dev/null || \
        $IPT -A OUTPUT -p $PROTO --dport 53 -d 1.1.1.1 -j ACCEPT
    $IPT -C OUTPUT -p $PROTO --dport 53 -d 1.0.0.1 -j ACCEPT 2>/dev/null || \
        $IPT -A OUTPUT -p $PROTO --dport 53 -d 1.0.0.1 -j ACCEPT
    $IPT -C OUTPUT -p $PROTO --dport 53 -j DROP 2>/dev/null || \
        $IPT -A OUTPUT -p $PROTO --dport 53 -j DROP
    # Encrypted DNS: dead (v4)
    $IPT -C OUTPUT -p $PROTO --dport 853 -j DROP 2>/dev/null || \
        $IPT -A OUTPUT -p $PROTO --dport 853 -j DROP

    # IPv6: local proxy only for DNS; everything else (incl. router RDNSS) dropped
    $IP6T -C OUTPUT -p $PROTO --dport 53 -d ::1 -j ACCEPT 2>/dev/null || \
        $IP6T -A OUTPUT -p $PROTO --dport 53 -d ::1 -j ACCEPT
    $IP6T -C OUTPUT -p $PROTO --dport 53 -j DROP 2>/dev/null || \
        $IP6T -A OUTPUT -p $PROTO --dport 53 -j DROP
    $IP6T -C OUTPUT -p $PROTO --dport 853 -j DROP 2>/dev/null || \
        $IP6T -A OUTPUT -p $PROTO --dport 853 -j DROP
done

# Known raw-IP LG endpoints (immune to hosts-file blocking)
for IP in 156.147.69.32 54.186.247.229; do
    $IPT -C OUTPUT -d $IP -j DROP 2>/dev/null || $IPT -A OUTPUT -d $IP -j DROP
done

echo "firewall v3: Cloudflare-only DNS allowlist + raw-IP drops applied"
