#!/bin/bash
# Moving-surface versions of ALL viewpoints (Robin, 18 Sep: the GIFs must look like flowing water): the surface texture is
# advected with the exact ground truth (moving_surface_control.py), then the same tracer compositing as dataset v3
# (synth_tracers.py, dense 0.0025 and sparse 0.0006, same seeds). Output out/v2/<view>_surfmove/{images, images_tracers_*, tracers_*}
# and Vectors_and_Images links v2_<view>_surfmove_{dense,sparse}. CPU only, skip-if-done.
cd "$(dirname "$0")"; P="$(dirname "$PWD")/v2_project"; PY=/opt/anaconda3/envs/pips2/bin/python
for v in Overview Path1 Path2 Path3 Path4 Path5 Path6 Path7 Low_1 Low_1_001 Low_1_002 Low_1_003 Low_2 low_angle Path3_clear high_angle_clear; do
  src=out/v2/v2_$v; dst=out/v2/v2_${v}_surfmove; [ -d "$src/images" ] || { echo "no source $v"; continue; }
  [ "$(ls $dst/images/*.png 2>/dev/null | wc -l)" -ge 201 ] || { echo "SURFMOVE $v $(date)"; nice -n 10 $PY moving_surface_control.py $src $dst > $dst.surfmove.log 2>&1 || { echo "FAILED surfmove $v"; continue; }; }
  for d in dense sparse; do
    dens=0.0025; [ $d = sparse ] && dens=0.0006
    [ -f "$dst/tracers_$d/trajs.npz" ] || { echo "TRACERS $v $d $(date)"; nice -n 10 $PY synth_tracers.py $dst --density $dens --tag _$d > $dst.tracers_$d.log 2>&1 || { echo "FAILED tracers $v $d"; continue; }; }
    s="v2_${v}_surfmove_$d"; mkdir -p "$P/Vectors_and_Images/$s"
    ln -sfn "$dst/images_tracers_$d" "$P/Vectors_and_Images/$s/images"; ln -sfn "$dst/vector" "$P/Vectors_and_Images/$s/vector"; ln -sfn "$dst/tracers_$d" "$P/Vectors_and_Images/$s/tracers"
  done
done; echo "SURFMOVE_ALL_DONE $(date)"
