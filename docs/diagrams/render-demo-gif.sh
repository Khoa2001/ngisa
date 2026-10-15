#!/usr/bin/env bash
# Renders docs/diagrams/ngisa-demo.html into docs/assets/ngisa-demo.gif and ngisa-demo.vi.gif.
# The page paints the scene at any time t, so every frame is one screenshot from a single headless Chrome
# (render-demo-frames.mjs). Needs Node 22, Google Chrome and ffmpeg. FPS (default 25) and COLORS (default 96) can be overridden.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
html="$here/ngisa-demo.html"
out="$here/../assets"
fps="${FPS:-25}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

for lang in en vi; do
  node "$here/render-demo-frames.mjs" "$html" "$lang" "$fps" "$tmp/$lang"
  name="ngisa-demo.gif"; [ "$lang" = vi ] && name="ngisa-demo.vi.gif"
  ffmpeg -y -loglevel error -framerate "$fps" -i "$tmp/$lang/%04d.png" \
    -vf "scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=${COLORS:-96}:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" \
    -loop 0 "$out/$name"
  echo "$name $(stat -f %z "$out/$name" 2>/dev/null || stat -c %s "$out/$name") bytes"
done
