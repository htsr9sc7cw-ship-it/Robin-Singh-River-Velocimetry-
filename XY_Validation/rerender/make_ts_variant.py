"""make_ts_variant.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

Speed ladder (PREREGISTRATION_v2_sweep.md, Sweep 2): save a copy of Basefile_a_TRACERS.blend with
domain time_scale = ts and its own cache folder. Never saves over the source file.
  $BLENDER --background Basefile_a_TRACERS.blend --python make_ts_variant.py -- --ts 0.5 --frames 1 360
"""

import bpy, os, sys, argparse

argv = sys.argv[sys.argv.index('--') + 1 :]
ap = argparse.ArgumentParser()
ap.add_argument('--ts', type=float, required=True)
ap.add_argument('--frames', nargs=2, type=int, required=True)
a = ap.parse_args(argv)
HERE = os.path.dirname(bpy.data.filepath)
dom = bpy.data.objects['Liquid Domain']
d = [m for m in dom.modifiers if m.type == 'FLUID'][0].domain_settings
print(
    'SOURCE time_scale',
    d.time_scale,
    'cache',
    d.cache_directory,
    'res',
    d.resolution_max,
    'domain gravity',
    tuple(d.gravity),
)
# [FIXLOG DATA-2] redirect the cache BEFORE touching any setting: Blender deletes a cache it considers outdated
d.cache_directory = '//cache_ts%g' % a.ts
d.time_scale = a.ts
d.cache_frame_start, d.cache_frame_end = a.frames
bpy.context.scene.frame_end = max(bpy.context.scene.frame_end, a.frames[1])
os.makedirs(bpy.path.abspath(d.cache_directory), exist_ok=True)
dst = os.path.join(HERE, 'Basefile_a_TRACERS_ts%g.blend' % a.ts)
assert not os.path.exists(dst), dst
bpy.ops.wm.save_as_mainfile(filepath=dst, copy=True)
print('SAVED', dst, 'time_scale', a.ts, 'cache', d.cache_directory, 'frames', a.frames, flush=True)
