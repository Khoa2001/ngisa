#!/usr/bin/env bash
# Renders docs/diagrams/ngisa-demo.html into docs/assets/ngisa-demo.gif and ngisa-demo.vi.gif.
# Needs Google Chrome (headless) and ffmpeg. Run from anywhere.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
html="$here/ngisa-demo.html"
out="$here/../assets"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Step durations (ms) live in the HTML so the page and the GIF agree.
durations=$(grep -o 'DURATIONS = \[[^]]*\]' "$html" | sed 's/.*\[\(.*\)\]/\1/' | tr -d ' ' | tr ',' ' ')
steps=($durations)

for lang in en vi; do
  list="$tmp/list-$lang.txt"
  : > "$list"
  for i in "${!steps[@]}"; do
    png="$tmp/$lang-$i.png"
    "$chrome" --headless=new --hide-scrollbars --disable-gpu \
      --window-size=960,540 --force-device-scale-factor=1 \
      --screenshot="$png" "file://$html?step=$i&lang=$lang" >/dev/null 2>&1
    echo "file '$png'" >> "$list"
    echo "duration $(awk "BEGIN{print ${steps[$i]}/1000}")" >> "$list"
  done
  # concat demuxer ignores the last duration unless the last file is repeated
  last="$tmp/$lang-$((${#steps[@]} - 1)).png"
  echo "file '$last'" >> "$list"

  name="ngisa-demo.gif"; [ "$lang" = vi ] && name="ngisa-demo.vi.gif"
  ffmpeg -y -loglevel error -f concat -safe 0 -i "$list" \
    -vf "scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];[b][p]paletteuse=dither=none" \
    -loop 0 "$out/$name"
  ls -l "$out/$name"
done
