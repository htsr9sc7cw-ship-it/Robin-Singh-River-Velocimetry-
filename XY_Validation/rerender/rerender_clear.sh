#!/bin/bash
# [FIXLOG R-1] re-render the two clear-water viewpoints with the clear material, then v3.2 GT + tracers.
cd "$(dirname "$0")"; B=/Applications/Blender.app/Contents/MacOS/Blender; P2=/opt/anaconda3/envs/pips2/bin/python; LOG=rerender_clear.log
echo "=== clear re-render start $(date)" | tee -a $LOG
render () { s=$1; cam=$2; tgt=$3; out=out/v2/$s
  for c0 in $(seq 80 50 280); do c1=$((c0+49)); [ $c1 -gt 280 ] && c1=280
    [ -f "$out/images/$(printf %04d $c1).png" ] && continue
    $B --background Basefile_a_TRACERS.blend --python bake_and_render.py -- render --camera $cam --frames $c0 $c1 --out $out --samples 48 --material clear --no-particles --size 512 512 $tgt >> $LOG 2>&1 || { echo "RENDER FAILED $s $c0" | tee -a $LOG; return 1; }
  done
  $P2 rasterise_gt.py $out >> $LOG 2>&1 || { echo "RASTER FAILED $s" | tee -a $LOG; return 1; }
  for tag in _sparse _dense; do dens=0.0006; [ "$tag" = "_dense" ] && dens=0.0025
    XYV_DATA=$out $P2 -W ignore synth_tracers.py $out --density $dens --tag $tag >> $LOG 2>&1 || { echo "TRACERS FAILED $s $tag" | tee -a $LOG; return 1; }
  done; echo "DONE $s $(date)" | tee -a $LOG
}
render v2_Path3_clear Camera.Path "--path-target Empty.003"
render v2_high_angle_clear Camera.initial_high_angle ""
n1=$(ls out/v2/v2_Path3_clear/tracers_dense/trajs.npz out/v2/v2_high_angle_clear/tracers_dense/trajs.npz 2>/dev/null | wc -l); [ "$n1" -eq 2 ] && echo "=== clear re-render DONE $(date)" | tee -a $LOG || echo "=== clear re-render INCOMPLETE ($n1/2) $(date)" | tee -a $LOG
