#!/bin/bash
# export THESIS_DRAFT.docx to a PDF through Pages (only for checking the layout / page numbers)
D="$(cd "$(dirname "$0")" && pwd)"; OUT="$D/_build/thesis_preview.pdf"; mkdir -p "$(dirname "$OUT")"
osascript -e 'tell application "Pages" to close every document saving no' 2>/dev/null; sleep 2
osascript <<EOF
tell application "Pages"
  open POSIX file "$D/THESIS_DRAFT.docx"
  delay 50
  set d to front document
  export d to POSIX file "$OUT" as PDF
  close d saving no
end tell
EOF
echo exported
