#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Crop all images matching a pattern using a single rectangle.

Usage:
  crop_rect.sh --in DIR --out DIR --glob "*.png" \
               --rect WxH+X+Y \
               [--test] [--dry-run]

Examples:
  crop_rect.sh --in raw --out cropped \
    --glob "*-FRONT.png" \
    --rect 1800x1100+120+160 --test
EOF
}

IN=""
OUT=""
GLOB=""
RECT=""
TEST=0
DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
  --in)
    IN="$2"
    shift 2
    ;;
  --out)
    OUT="$2"
    shift 2
    ;;
  --glob)
    GLOB="$2"
    shift 2
    ;;
  --rect)
    RECT="$2"
    shift 2
    ;;
  --test)
    TEST=1
    shift
    ;;
  --dry-run)
    DRY=1
    shift
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown arg: $1"
    usage
    exit 2
    ;;
  esac
done

[[ -n "$IN" && -n "$OUT" && -n "$GLOB" && -n "$RECT" ]] || usage

command -v magick >/dev/null || {
  echo "ImageMagick required (magick)"
  exit 1
}

mkdir -p "$OUT"

run() {
  if [[ "$DRY" -eq 1 ]]; then
    printf "DRY: "
    printf "%q " "$@"
    echo
  else
    "$@"
  fi
}

shopt -s nullglob
FILES=("$IN"/$GLOB)
shopt -u nullglob

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No files matched: $IN/$GLOB" >&2
  exit 1
fi

if [[ "$TEST" -eq 1 ]]; then
  FILES=("${FILES[0]}")
  echo "TEST MODE → $(basename "${FILES[0]}")"
fi

for f in "${FILES[@]}"; do
  base="$(basename "$f")"
  out="$OUT/$base"

  echo "Cropping $base"

  run magick "$f" -crop "$RECT" +repage "$out"

done
