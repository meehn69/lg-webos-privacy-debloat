#!/bin/sh
# Fix preload config + runtime policy + boot hook categories (TV-side)
CONF=/var/preferences/webos-preload-manager-conf.json

# 1. Persisted allowedApps: the RAM hogs go false
sed -i 's/"youtube.leanback.v4":true/"youtube.leanback.v4":false/' "$CONF"
sed -i 's/"netflix":true/"netflix":false/' "$CONF"
sed -i 's/"amazon":true/"amazon":false/' "$CONF"
sed -i 's/"com.webos.app.lgchannels":true/"com.webos.app.lgchannels":false/' "$CONF"
sed -i 's/"com.webos.app.voice":true/"com.webos.app.voice":false/' "$CONF"
echo "CONF-NOW:"
grep -o '"youtube.leanback.v4":[a-z]*\|"netflix":[a-z]*\|"amazon":[a-z]*\|"com.webos.app.lgchannels":[a-z]*\|"com.webos.app.voice":[a-z]*' "$CONF"

# 2. Runtime preload policy per app (immediate)
for A in youtube.leanback.v4 netflix amazon com.webos.app.lgchannels com.webos.app.voice; do
    luna-send -n 1 "luna://com.webos.service.preloadmanager/setPreloadPolicy" "{\"application\":{\"id\":\"$A\",\"isEnabled\":false}}" >/dev/null 2>&1
done
echo "POLICY-SET"

# 3. Close the resident preloaded YouTube app if alive
luna-send -n 1 "luna://com.webos.applicationManager/closeByAppId" '{"id":"youtube.leanback.v4"}' >/dev/null 2>&1
echo "CLOSED"

# 4. Boot hook: re-apply ALL categories, not just defaults
sed -i 's/webos-debloat.sh" --apply /webos-debloat.sh" --apply --only ad,sdk,demo,remote,promo,visible,extras /' /var/lib/webosbrew/init.d/50-debloat
echo "HOOK-NOW:"
grep apply /var/lib/webosbrew/init.d/50-debloat

echo "MEM-AFTER:"
grep MemAvailable /proc/meminfo
