"""bake_and_render.py

Thesis section: 4.2, 4.3
Inputs: Blender file with the fluid scene, camera name, frame range
Outputs: fluid cache, rendered frames, motion-vector pass

R3/R4/R6: bake the fluid cache and render frames + Vector pass from Basefile_a_TRACERS.blend.

  BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
  $BLENDER --background Basefile_a_TRACERS.blend --python bake_and_render.py -- bake   --frames 1 40 [--res 200]
  $BLENDER --background Basefile_a_TRACERS.blend --python bake_and_render.py -- render --camera Camera.Low_1 --frames 100 130 --out out/pilot_Low_1
  $BLENDER --background Basefile_a_TRACERS.blend --python bake_and_render.py -- cameras --frame 80 --out out/camera_probe

Everything after `--` belongs to this script.  Nothing is saved back to the .blend unless
--save is given (the bake writes only the cache folder).

Output layout (matches Vectors_and_Images/<scene>/):
  <out>/images/NNNN.png       8-bit RGBA
  <out>/vector/VectorNNNN.exr float32 R,G = Blender Vector pass (R,G) as the originals
  <out>/depth/DepthNNNN.exr
  <out>/render_log.csv        frame, seconds
"""

import bpy
import os
import sys
import time
import argparse

argv = sys.argv[sys.argv.index('--') + 1 :] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('cmd', choices=['bake', 'render', 'cameras'])
ap.add_argument('--frames', nargs=2, type=int, default=[1, 40])
ap.add_argument('--frame', type=int, default=80)
ap.add_argument('--res', type=int, default=None, help='domain resolution_max override')
ap.add_argument('--camera', default='Camera.Low_1')
ap.add_argument('--out', default='out/pilot')
ap.add_argument('--samples', type=int, default=None)
ap.add_argument('--save', action='store_true')
ap.add_argument(
    '--material', choices=['muddy', 'clear'], default='muddy', help='water material on the domain'
)
ap.add_argument('--path-target', default=None, help='for Camera.Path: Empty.001..Empty.007')
ap.add_argument(
    '--size',
    nargs=2,
    type=int,
    default=[512, 512],
    help='render width height (Overview is 1024 512)',
)
ap.add_argument(
    '--no-particles',
    action='store_true',
    help='render the water surface only; tracers are composited afterwards (synth_tracers.py)',
)
a = ap.parse_args(argv)

HERE = os.path.dirname(bpy.data.filepath)
scene = bpy.context.scene
dom = bpy.data.objects['Liquid Domain']
d = [m for m in dom.modifiers if m.type == 'FLUID'][0].domain_settings


def enable_metal():
    """Cycles device prefs are user prefs, not saved in the .blend: set them every run."""
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for dev in prefs.devices:
        dev.use = True  # GPU + CPU hybrid (Apple Silicon unified memory)
    scene.cycles.device = 'GPU'
    print('DEVICES', [(dv.name, dv.type, dv.use) for dv in prefs.devices], flush=True)


def override():
    return bpy.context.temp_override(
        object=dom,
        active_object=dom,
        selected_objects=[dom],
        scene=scene,
        view_layer=scene.view_layers[0],
    )


def do_bake():
    f0, f1 = a.frames
    if a.res:
        d.resolution_max = a.res
    d.cache_frame_start = f0
    d.cache_frame_end = f1
    d.cache_type = 'MODULAR'
    os.makedirs(bpy.path.abspath(d.cache_directory), exist_ok=True)
    print(
        'BAKE res',
        d.resolution_max,
        'frames',
        f0,
        f1,
        'cache',
        bpy.path.abspath(d.cache_directory),
        flush=True,
    )
    log = open(os.path.join(HERE, 'bake_log.txt'), 'a')
    for stage, op in (
        ('data', bpy.ops.fluid.bake_data),
        ('mesh', bpy.ops.fluid.bake_mesh),
        ('particles', bpy.ops.fluid.bake_particles),
    ):
        t = time.time()
        with override():
            r = op()
        dt = time.time() - t
        msg = 'BAKE %s frames %d-%d res %d : %s in %.1f s (%.2f s/frame)' % (
            stage,
            f0,
            f1,
            d.resolution_max,
            r,
            dt,
            dt / max(1, f1 - f0 + 1),
        )
        print(msg, flush=True)
        log.write(msg + '\n')
        log.flush()
    log.close()
    if a.save:
        bpy.ops.wm.save_mainfile()


def set_outputs(outdir):
    outdir = os.path.abspath(outdir)
    scene.render.use_compositing = True
    scene.use_nodes = True
    for sub in ('images', 'vector_cycles', 'depth'):
        os.makedirs(os.path.join(outdir, sub), exist_ok=True)
    nt = scene.compositing_node_group
    fo = [n for n in nt.nodes if n.type == 'OUTPUT_FILE'][0]
    fo.mute = False
    fo.directory = outdir + '/'
    # input names become file prefixes: Vector####.exr, Depth####.exr; move them after render
    return outdir, fo


def apply_scene_variant():
    """Water material (the originals have 'clear' and 'muddy0.4' scenes) and Path-camera position."""
    scene.render.resolution_x, scene.render.resolution_y = a.size
    if a.no_particles:
        for ps in dom.particle_systems:
            ps.settings.render_type = 'NONE'
        dom.show_instancer_for_render = True
    mat = bpy.data.materials['Water_clear' if a.material == 'clear' else 'Water_muddy']
    dom.data.materials[0] = mat
    if a.path_target:
        cam = bpy.data.objects['Camera.Path']
        [c for c in cam.constraints if c.type == 'COPY_LOCATION'][0].target = bpy.data.objects[
            a.path_target
        ]
    print('VARIANT material', mat.name, 'path_target', a.path_target, flush=True)


def do_render():
    enable_metal()
    apply_scene_variant()
    f0, f1 = a.frames
    scene.camera = bpy.data.objects[a.camera]
    if a.samples:
        scene.cycles.samples = a.samples
    outdir, fo = set_outputs(a.out)
    log = open(os.path.join(outdir, 'render_log.csv'), 'a')
    log.write('frame,seconds\n')
    print(
        'RENDER camera',
        a.camera,
        'frames',
        f0,
        f1,
        'samples',
        scene.cycles.samples,
        'device',
        scene.cycles.device,
        '->',
        outdir,
        flush=True,
    )
    for fr in range(f0, f1 + 1):
        t = time.time()
        scene.frame_set(fr)
        scene.render.filepath = os.path.join(outdir, 'images', '%04d' % fr)
        bpy.ops.render.render(write_still=True)
        # File Output writes <dir>/Vector<frame>.exr and Depth<frame>.exr -> sort into subfolders
        # Blender 5.2 names them <input>.exr (no frame number) -> rename to the original layout
        for name, sub in (
            ('Vector', 'vector_cycles'),
            ('Depth', 'depth'),
        ):  # Cycles pass kept apart: GT comes from the particles
            for src in (
                os.path.join(outdir, '%s.exr' % name),
                os.path.join(outdir, '%s%04d.exr' % (name, fr)),
            ):
                if os.path.exists(src):
                    os.replace(src, os.path.join(outdir, sub, '%s%04d.exr' % (name, fr)))
        dt = time.time() - t
        print('RENDER frame %d in %.1f s' % (fr, dt), flush=True)
        log.write('%d,%.2f\n' % (fr, dt))
        log.flush()
    log.close()


def do_cameras():
    enable_metal()
    outdir, fo = set_outputs(a.out)
    fo.mute = True
    scene.frame_set(a.frame)
    if a.samples:
        scene.cycles.samples = a.samples
    for cam in [o for o in bpy.data.objects if o.type == 'CAMERA']:
        scene.camera = cam
        scene.render.filepath = os.path.join(outdir, 'images', cam.name.replace('.', '_'))
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print('CAMERA %s rendered in %.1f s' % (cam.name, time.time() - t), flush=True)


{'bake': do_bake, 'render': do_render, 'cameras': do_cameras}[a.cmd]()
print('DONE', a.cmd, flush=True)
