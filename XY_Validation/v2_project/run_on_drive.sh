#!/bin/bash
# Drive-safe runner: bash run_on_drive.sh <script> [args]  — relaunches the (resumable) script whenever the external drive
# drops and comes back (it returns as "Drive Von Robin 1"; we remount disk5s1 under its proper name). Ends when the
# script writes its end marker (a line containing END_MARKER, default "=== .* end") to $LOG. Nothing stored on the Mac
# except this loop's own log in the session scratchpad.
X="/Volumes/Drive Von Robin/THESIS ORIGINAL  /XY_Validation"; SCRIPT="$1"; shift; LOG="$X/v2_project/drive_watch.log"
WLOG="${WATCH_LOG:-/private/tmp/claude-501/-Users-robinsingh-Desktop-Documents/be05ab9c-d215-46c8-87b0-d6d322784e37/scratchpad/run_on_drive.log}"
remount() { diskutil unmount disk5s1 >/dev/null 2>&1; sleep 3; diskutil mount disk5s1 >/dev/null 2>&1; sleep 5; }
while true; do
  if [ ! -d "$X/v2_project" ]; then echo "$(date) drive missing -> remount" >> "$WLOG"; remount; sleep 20; continue; fi
  if grep -q "=== .* end" "$X/${SCRIPT%.sh}.log" 2>/dev/null; then echo "$(date) script finished" >> "$WLOG"; exit 0; fi
  swap=$(sysctl -n vm.swapusage | sed -E "s/.*used = ([0-9]+)[.0-9]*M.*/\1/"); [ "${swap:-0}" -gt 2500 ] && { echo "$(date) swap ${swap}M in use -> waiting" >> "$WLOG"; sleep 120; continue; }   # memory guard (8 GB Mac)
  if ! pgrep -f "bash $X/$SCRIPT" >/dev/null && ! pgrep -f "bash $(basename $SCRIPT)" >/dev/null; then
    echo "$(date) (re)launch $SCRIPT" >> "$WLOG"; echo "$(date) (re)launch" >> "$LOG"
    ( cd "$X/$(dirname $SCRIPT)" && nohup caffeinate -i bash "$(basename $SCRIPT)" "$@" >> "$X/${SCRIPT%.sh}.log" 2>&1 & )
    sleep 60
  fi
  sleep 60
done
