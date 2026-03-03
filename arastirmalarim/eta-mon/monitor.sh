#!/bin/bash

PORT=7777

sudo tcpdump -i any -A tcp dst port $PORT -l -n 2>/dev/null | while read -r line; do
    if echo "$line" | grep -q 'ebaqr'; then
        # 'ebaqronline:' kelimesinden itibaren kes
        clean_part=$(echo "$line" | sed -n 's/.*\(ebaqronline:.*\)/\1/p')
        logger -t ETA "$clean_part"
    fi
done
