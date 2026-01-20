#!/usr/bin/env bash
set -u
set -o pipefail

usage() {
  cat <<'EOF'
Usage:
  stitch_views.sh --in IN_DIR --out OUT_DIR [--verbose] [--one]
                  [--front-tag "FRONT.png"] [--left-tag "LEFT.png"] [--top-tag "TOP.png"]
                  [--bg white|none]
                  [--text "line1\nline2"] [--font "DejaVu-Sans"] [--pointsize 56] [--margin 80,120]

Layout:
  [ TEXT/BLANK ] [   TOP   ]
  [   LEFT     ] [  FRONT  ]

Notes:
- No `magick identify` used.
- Assumes TOP/LEFT/FRONT are the same size (true after crop).
- Separator is detected per set from the FRONT filename.
EOF
}

IN_DIR=""
OUT_DIR=""
FRONT_TAG="FRONT.png"
LEFT_TAG="LEFT.png"
TOP_TAG="TOP.png"
BG="white"
ONE=0
VERBOSE=0

TEXT="" # optional
FONT="DejaVu-Sans"
POINTSIZE=56
MARGIN_X=80
MARGIN_Y=120

while [[ $# -gt 0 ]]; do
  case "$1" in
  --in)
    IN_DIR="$2"
    shift 2
    ;;
  --out)
    OUT_DIR="$2"
    shift 2
    ;;

  --front-tag)
    FRONT_TAG="$2"
    shift 2
    ;;
  --left-tag)
    LEFT_TAG="$2"
    shift 2
    ;;
  --top-tag)
    TOP_TAG="$2"
    shift 2
    ;;

  --bg)
    BG="$2"
    shift 2
    ;;
  --one)
    ONE=1
    shift
    ;;
  --verbose)
    VERBOSE=1
    shift
    ;;

  --text)
    TEXT="$2"
    shift 2
    ;;
  --font)
    FONT="$2"
    shift 2
    ;;
  --pointsize)
    POINTSIZE="$2"
    shift 2
    ;;
  --margin)
    IFS=',' read -r MARGIN_X MARGIN_Y <<<"$2"
    shift 2
    ;;

  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown arg: $1" >&2
    usage
    exit 2
    ;;
  esac
done

[[ -n "$IN_DIR" && -n "$OUT_DIR" ]] || {
  echo "Missing --in/--out" >&2
  usage
  exit 2
}

command -v magick >/dev/null 2>&1 || {
  echo "Need ImageMagick ($(magick))." >&2
  exit 1
}

mkdir -p "$OUT_DIR"

shopt -s nullglob
front_files=("$IN_DIR"/*"$FRONT_TAG")
shopt -u nullglob

echo "Searching: $IN_DIR/*$FRONT_TAG"
echo "Found: ${#front_files[@]} FRONT file(s)"

if [[ ${#front_files[@]} -eq 0 ]]; then
  echo "ERROR: no FRONT files matched." >&2
  exit 1
fi

if [[ "$ONE" -eq 1 ]]; then
  front_files=("${front_files[0]}")
  echo "ONE mode -> $(basename "${front_files[0]}")"
fi

# Parse "<base><sep>FRONT_TAG"
# sep = trailing run of non-alnum chars immediately before FRONT_TAG (e.g. "-", "_", "__", "--", or "")
parse_front() {
  local filename="$1"
  local tag="$2"

  [[ "$filename" == *"$tag" ]] || return 1

  local stem="${filename%$tag}" # e.g. "FSRL2-10-"
  local sep=""

  while [[ -n "$stem" && "${stem: -1}" =~ [^[:alnum:]] ]]; do
    sep="${stem: -1}$sep"
    stem="${stem::-1}"
  done

  printf '%s\n%s\n' "$stem" "$sep"
}

written=0
skipped=0
failed=0

for front_path in "${front_files[@]}"; do
  front_file="$(basename "$front_path")"

  mapfile -t parsed < <(parse_front "$front_file" "$FRONT_TAG" || true)
  if [[ ${#parsed[@]} -ne 2 ]]; then
    echo "Skipping: cannot parse FRONT filename: $front_file" >&2
    ((skipped++))
    continue
  fi

  base="${parsed[0]}"
  sep="${parsed[1]}"

  left_path="$IN_DIR/${base}${sep}${LEFT_TAG}"
  top_path="$IN_DIR/${base}${sep}${TOP_TAG}"

  if [[ ! -f "$left_path" || ! -f "$top_path" ]]; then
    echo "Skipping: $front_file" >&2
    [[ ! -f "$left_path" ]] && echo "  missing LEFT: $(basename "$left_path")" >&2
    [[ ! -f "$top_path" ]] && echo "  missing TOP : $(basename "$top_path")" >&2
    ((skipped++))
    continue
  fi

  out="$OUT_DIR/${base}${sep}ORTHO.png"

  if [[ "$VERBOSE" -eq 1 ]]; then
    echo "----"
    echo "FRONT: $front_file"
    echo "  base='$base' sep='$sep'"
    echo "  LEFT: $(basename "$left_path")"
    echo "  TOP : $(basename "$top_path")"
    echo "  OUT : $(basename "$out")"
  fi

  # Build top-left tile by cloning FRONT and colorizing to BG, then optionally annotate text.
  # Then:
  #   row1 = [tile] + [TOP]
  #   row2 = [LEFT] + [FRONT]
  #   out  = row1 stacked over row2
  if [[ -n "$TEXT" ]]; then
    if magick \
      \( "$front_path" -alpha off -fill "$BG" -colorize 100 \
      -gravity northwest -font "$FONT" -pointsize "$POINTSIZE" -fill black \
      -annotate +"$MARGIN_X"+"$MARGIN_Y" "$TEXT" \) \
      \( "$top_path" \) +append \
      \( "$left_path" "$front_path" +append \) \
      -append \
      "$out"; then
      echo "Wrote: $out"
      ((written++))
    else
      echo "FAILED stitch: $front_file" >&2
      ((failed++))
    fi
  else
    if magick \
      \( "$front_path" -alpha off -fill "$BG" -colorize 100 \) \
      \( "$top_path" \) +append \
      \( "$left_path" "$front_path" +append \) \
      -append \
      "$out"; then
      echo "Wrote: $out"
      ((written++))
    else
      echo "FAILED stitch: $front_file" >&2
      ((failed++))
    fi
  fi
done

echo "==== Summary ===="
echo "Written: $written"
echo "Skipped: $skipped"
echo "Failed : $failed"

[[ $written -gt 0 ]] || exit 1
