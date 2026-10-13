#!/bin/sh
# struggleavg.sh RPS ARM : mean P1/CPU hits over DELAY 0..7
for d in 0 1 2 3 4 5 6 7; do DELAY=$d python rushstrug.py 9 420 "$1" "$2" 2>&1 | grep rps; done | awk '{for(i=1;i<=NF;i++){if($i=="P1")p+=$(i+1); if($i=="CPU")c+=$(i+1); if($i=="struggle")l+=$(i+1)} n++} END {printf "P1 %.1f CPU %.1f len %.1f (n=%d)\n", p/n, c/n, l/n, n}'
