#!/bin/zsh
# Speed ladder (PREREGISTRATION_v2_sweep.md Sweep 2). Per rung: bake -> calibrate -> render 2 cameras
# (surface only) -> particle GT -> rasterise -> composited tracers sparse/dense.  Output out/v2/<scene>_ts<ts>/
set -u
B=/Applications/Blender.app/Contents/MacOS/Blender
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
P2=/opt/anaconda3/envs/pips2/bin/python
run_rung () {
  ts=$1; f0=$2; f1=$3; bake_end=$4; cal0=$5; cal1=$6
  BL="Basefile_a_TRACERS_ts${ts}.blend"; LOG="ladder_ts${ts}.log"
  echo "=== RUNG ts=$ts $(date)" | tee -a $LOG
  n=$(ls cache_ts${ts}/data 2>/dev/null | grep -c vel_ || true)
  if [ "$n" -lt "$bake_end" ]; then
    $B --background $BL --python bake_and_render.py -- bake --frames 1 $bake_end >> $LOG 2>&1 || { echo "BAKE FAILED ts=$ts" | tee -a $LOG; return 1; }
  fi
  $B --background $BL --python calibrate_vscale_voxel.py -- --frames $cal0 $cal1 --n 60000 >> $LOG 2>&1
  VS=$(python3 -c "
import re,sys
t=open('vscale_voxel_ts${ts}.txt').read()
# envelope peak on filling frames: highest inside-fraction over all k, first frame line
best=[]
for line in t.splitlines():
    if '|' in line and not line.startswith('frame'):
        pairs=[(float(a),float(b)) for a,b in re.findall(r'\*?([\d.]+):([\d.]+)',line.split('|')[1])]
        best.append(max(pairs,key=lambda p:p[1])[0])
import statistics; print('%.3f'%statistics.median(best))")
  echo "VSCALE_RUNG ts=$ts measured k=$VS; GT rasterised with the BASE value 1.35 for ladder consistency (FIXLOG L8)" | tee -a $LOG
  for cam in Camera.Low_1 Camera.Low_1.001; do
    sc="v2_${cam#Camera.}_ts${ts}"; sc=${sc//./_}; out="out/v2/$sc"
    echo "--- $sc frames $f0-$f1 $(date)" | tee -a $LOG
    for c0 in $(seq $f0 50 $f1); do c1=$(( c0+49 )); [ $c1 -gt $f1 ] && c1=$f1
      [ -f "$out/images/$(printf %04d $c1).png" ] && continue
      $B --background $BL --python bake_and_render.py -- render --camera $cam --frames $c0 $c1 --out $out --samples 48 --material muddy --no-particles --size 512 512 >> $LOG 2>&1 || { echo "RENDER FAILED $sc $c0" | tee -a $LOG; return 1; }
    done
    if [ ! -f "$out/vector/Vector$(printf %04d $f1).exr" ]; then
      $B --background $BL --python gt_from_particles.py -- --camera $cam --frames $f0 $f1 --out $out --size 512 512 --vscale 1.35 >> $LOG 2>&1 || { echo "GT FAILED $sc" | tee -a $LOG; return 1; }
      $P2 rasterise_gt.py $out >> $LOG 2>&1 || { echo "RASTER FAILED $sc" | tee -a $LOG; return 1; }
    fi
    # [FIXLOG L1] zsh does not word-split unquoted variables: explicit pairs instead of `set -- $td`
    for tag in _sparse _dense; do
      dens=0.0006; [ "$tag" = "_dense" ] && dens=0.0025
      [ -f "$out/tracers$tag/trajs.npz" ] && continue
      $P2 -W ignore synth_tracers.py $out --density $dens --tag $tag >> $LOG 2>&1 || { echo "TRACERS FAILED $sc $tag" | tee -a $LOG; return 1; }
    done
    echo "DONE $sc $(date)" | tee -a $LOG
  done
}
run_rung 0.5  160 360 360 40 60
run_rung 0.25 320 520 520 80 120
echo "LADDER DONE $(date)" | tee -a ladder_done.txt
