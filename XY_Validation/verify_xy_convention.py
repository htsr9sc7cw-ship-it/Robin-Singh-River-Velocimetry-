"""verify_xy_convention.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md

verify_xy_convention.py -- prove every converted X,Y file matches the confirmed U,V convention.

WHY THIS EXISTS
---------------
The question raised was whether the X,Y files were built on a wrong reading of U and V. They were
not, but "I checked three scenes" is not an answer for a thesis. This checks ALL 4,515 files.

THE CONVENTION BEING VERIFIED
-----------------------------
Blender tutorial section 6.1.2, verbatim:

    "The Red and Green channel contain the X and Y displacement
     from the current frame to previous frame."

    R = X displacement = HORIZONTAL
    G = Y displacement = VERTICAL
    both point BACKWARD in time (current -> previous)
    V is negated in image coordinates: Blender's Y axis is up, image rows go down

So every stored position file must satisfy, exactly:

    X = x + R          Y = y - G

This is exact arithmetic -- no interpolation, no resampling -- so the pass criterion is
BIT-EQUALITY, not a tolerance. Any nonzero difference is a real defect.

THE CONTROL THAT MAKES THIS MEAN SOMETHING
------------------------------------------
A test that only confirms the expected answer proves nothing. So each file is also scored against
the WRONG-SIGN hypothesis (Y = y + G). That must fail loudly. If it ever came out near zero too,
the test would be incapable of telling right from wrong and the "pass" would be worthless.

HOW TO RUN IT YOURSELF (PyCharm)
--------------------------------
Interpreter: the `pips2` conda env. Right-click -> Run.
    --workers 5     parallel scene workers
    --scene NAME    just one scene
Exit status is 0 only if every file passes.
"""

import os
import sys
import glob
import time
import argparse
import numpy as np
import OpenEXR as oexr
import Imath
import array as arr
from multiprocessing import Pool

FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.environ.get('XYV_DATA') or os.path.join(ROOT, 'Vectors_and_Images')
XY = os.environ.get('XY_FORMAT_OUT') or os.path.join(ROOT, 'XY_Format')
REPORT = os.path.join(HERE, 'out', 'XY_CONVENTION_VERIFICATION.txt')


def two_channels(path):
    """Read only R and G -- the two we need. Reading all four would be ~2x the work."""
    f = oexr.InputFile(path)
    dw = f.header()['dataWindow']
    W = dw.max.x - dw.min.x + 1
    H = dw.max.y - dw.min.y + 1
    R = np.frombuffer(f.channel('R', FLOAT), dtype=np.float32).reshape(H, W)
    G = np.frombuffer(f.channel('G', FLOAT), dtype=np.float32).reshape(H, W)
    f.close()
    return R, G, H, W


def digits(p):
    return ''.join(c for c in os.path.basename(p) if c.isdigit())


def check_scene(scene):
    t0 = time.time()
    svs = sorted(glob.glob(os.path.join(SRC, scene, 'vector', '*.exr')))
    xys = sorted(glob.glob(os.path.join(XY, scene, 'dense_xy', '*.exr')))
    r = dict(
        scene=scene,
        n_src=len(svs),
        n_xy=len(xys),
        files=0,
        maxX=0.0,
        maxY=0.0,
        min_wrong=np.inf,
        issues=[],
    )

    if len(svs) != len(xys):
        r['issues'].append('file count %d vs %d' % (len(svs), len(xys)))
    # frame numbering must correspond one-for-one; a one-frame slip would still give small
    # residuals because consecutive frames look alike, so this is checked explicitly
    for a, b in zip(svs, xys):
        if digits(a) != digits(b):
            r['issues'].append('numbering %s vs %s' % (os.path.basename(a), os.path.basename(b)))
            break

    grid = {}
    for a, b in zip(svs, xys):
        R, G, H, W = two_channels(a)
        X, Y, H2, W2 = two_channels(b)
        if (H, W) != (H2, W2):
            r['issues'].append('%s resolution %dx%d vs %dx%d' % (digits(a), W, H, W2, H2))
            continue
        if (H, W) not in grid:
            yy, xx = np.mgrid[0:H, 0:W]
            grid[(H, W)] = (xx.astype(np.float32), yy.astype(np.float32))
        xx, yy = grid[(H, W)]
        r['maxX'] = max(r['maxX'], float(np.abs(X - (xx + R)).max()))
        r['maxY'] = max(r['maxY'], float(np.abs(Y - (yy - G)).max()))
        # the control: the wrong-sign hypothesis must be badly wrong
        r['min_wrong'] = min(r['min_wrong'], float(np.abs(Y - (yy + G)).max()))
        r['files'] += 1

    r['seconds'] = time.time() - t0
    r['passed'] = (
        r['maxX'] == 0.0
        and r['maxY'] == 0.0
        and not r['issues']
        and r['files'] == len(svs)
        and r['files'] > 0
    )
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--scene', default=None)
    a = ap.parse_args()
    scenes = (
        [a.scene]
        if a.scene
        else sorted(d for d in os.listdir(SRC) if os.path.isdir(os.path.join(SRC, d, 'vector')))
    )
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)

    hdr = []
    hdr.append('=' * 100)
    hdr.append('VERIFYING EVERY X,Y FILE AGAINST THE CONFIRMED BLENDER CONVENTION')
    hdr.append('=' * 100)
    hdr.append('Tutorial 6.1.2: "The Red and Green channel contain the X and Y displacement')
    hdr.append('                 from the current frame to previous frame."')
    hdr.append('  R = horizontal, G = vertical, backward in time, V negated for image rows.')
    hdr.append('  Required exactly:   X = x + R     Y = y - G')
    hdr.append('  Pass = BIT-EQUALITY (exact arithmetic, so any nonzero difference is a defect).')
    hdr.append('  Control = the wrong-sign form Y = y + G, which must fail loudly.')
    hdr.append('')
    print('\n'.join(hdr))
    print(
        '%-44s %6s %10s %10s %12s %7s'
        % ('scene', 'files', 'max|dX|', 'max|dY|', 'wrong-sign', 'result')
    )
    print('-' * 100)

    T0 = time.time()
    rows = []
    if len(scenes) == 1:
        rows.append(check_scene(scenes[0]))
    else:
        with Pool(processes=a.workers) as p:
            for r in p.imap_unordered(check_scene, scenes):
                rows.append(r)
    rows.sort(key=lambda r: r['scene'])

    lines = []
    for r in rows:
        line = '%-44s %6d %10.2e %10.2e %12.1f %7s' % (
            r['scene'].replace('Elbersdorf_3ms_', '')[:44],
            r['files'],
            r['maxX'],
            r['maxY'],
            r['min_wrong'],
            'PASS' if r['passed'] else 'FAIL',
        )
        print(line)
        lines.append(line)
        for i in r['issues']:
            print('      ! %s' % i)
            lines.append('      ! %s' % i)

    el = time.time() - T0
    bad = [r for r in rows if not r['passed']]
    tot = sum(r['files'] for r in rows)
    weakest = min((r['min_wrong'] for r in rows), default=0)

    tail = []
    tail.append('-' * 100)
    tail.append(
        '%d files across %d scenes checked in %.1f s (%.1f min, %d workers)'
        % (tot, len(rows), el, el / 60, a.workers)
    )
    tail.append('scenes passed: %d / %d' % (len(rows) - len(bad), len(rows)))
    tail.append('')
    tail.append(
        'CONTROL: the smallest wrong-sign error anywhere was %.1f px. The test can tell' % weakest
    )
    tail.append('right from wrong -- a "pass" here is discrimination, not an inability to fail.')
    if bad:
        tail.append('')
        tail.append('FAILED: ' + ', '.join(r['scene'] for r in bad))
        tail.append('Regenerate only those:  python convert_uv_to_xy.py --dense --scene <name>')
    else:
        tail.append('')
        tail.append('RESULT: every X,Y file already matches the confirmed convention exactly.')
        tail.append('Regeneration would produce byte-identical files and is not needed.')
    tail.append('=' * 100)
    print('\n'.join(tail))

    with open(REPORT, 'w') as f:
        f.write('\n'.join(hdr) + '\n')
        f.write(
            '%-44s %6s %10s %10s %12s %7s\n'
            % ('scene', 'files', 'max|dX|', 'max|dY|', 'wrong-sign', 'result')
        )
        f.write('-' * 100 + '\n' + '\n'.join(lines) + '\n' + '\n'.join(tail) + '\n')
    print('\nreport written to %s' % REPORT)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
