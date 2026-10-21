"""Figure (reach layout) of the simulated reach and the camera positions.
Output: results/figures/figY_reach_layout.png      Run:  python fig_3_06_reach_layout.py
Positions are read from a copy of the project file (`2023-10-22 Basefile a.blend`) with Blender's Python interface (values stored in `reach_layout.json`);
the liquid domain is 14.3 m x 7.8 m x 1.66 m and the water flows towards negative y (Sect. 3.2)."""
import json
import os

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

import tud_style as tud

HERE = os.path.dirname(os.path.abspath(__file__))
XY = os.path.dirname(HERE)
OUT = os.path.join(XY, 'results', 'figures')
tud.apply()
D = json.load(open(os.path.join(HERE, 'reach_layout.json')))
CAM, OBJ = D['cameras'], D['objects']
dom = [o for o in OBJ if o['name'] == 'Liquid Domain'][0]
cx, cy = dom['loc'][0], dom['loc'][1]
w, h = dom['dim'][0], dom['dim'][1]
LABEL = {'Camera.initial_high_angle': 'high angle', 'Camera.initial_low_angle': 'low angle', 'Camera.Low_1': 'Low_1', 'Camera.Low_1.001': 'Low_1.001',
         'Camera.Low_1.002': 'Low_1.002', 'Camera.Low_1.003': 'Low_1.003', 'Camera.Low_2': 'Low_2', 'Camera.Overview': 'Overview'}
OFFSET = {'Camera.initial_high_angle': (-0.2, 0.55), 'Camera.initial_low_angle': (0.0, -0.55), 'Camera.Low_1': (-0.95, 0.0), 'Camera.Low_1.001': (-0.2, -0.6),
          'Camera.Low_1.002': (0.0, -0.55), 'Camera.Low_1.003': (0.0, -0.55), 'Camera.Low_2': (0.3, 0.35), 'Camera.Overview': (-1.2, 1.0)}


def main():
    fig, (a, b) = plt.subplots(2, 1, figsize=(7.2, 6.4), gridspec_kw={'height_ratios': [3.0, 1.35], 'hspace': 0.45})
    # (a) top view
    a.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fc=tud.BLUE_TINT, ec=tud.BLUE, lw=1.4, zorder=1))
    a.add_patch(FancyArrowPatch((cx - w / 2 + 0.7, cy + h / 2 - 0.35), (cx - w / 2 + 0.7, cy - h / 2 + 0.45), arrowstyle='-|>', mutation_scale=14, color=tud.BLUE, lw=1.6, zorder=2))
    a.text(cx - w / 2 + 0.95, cy, 'flow', color=tud.BLUE, fontsize=8, rotation=90, va='center', ha='left')
    a.text(cx - w / 2 + 1.3, cy + h / 2 - 0.2, 'inflow side', fontsize=7.5, color=tud.GREY, va='top')
    a.text(cx - w / 2 + 1.3, cy - h / 2 + 0.2, 'outflow side', fontsize=7.5, color=tud.GREY, va='bottom')
    for k, c in CAM.items():
        if k in LABEL:
            x, y = c['loc'][0], c['loc'][1]
            dx, dy = c['dir'][0], c['dir'][1]
            n = (dx ** 2 + dy ** 2) ** 0.5
            if n > 0.2:
                a.add_patch(FancyArrowPatch((x, y), (x + 1.5 * dx / n, y + 1.5 * dy / n), arrowstyle='-|>', mutation_scale=10, color=tud.BLUE_MID, lw=1.2, zorder=3))
            a.plot([x], [y], 's', color=tud.BLUE, ms=5.5, zorder=4)
            ox, oy = OFFSET[k]
            if k == 'Camera.Overview':
                a.plot([x, x + 0.45 * ox], [y, y + oy - 0.2], '-', color=tud.GREY, lw=0.7, zorder=3)
            a.text(x + ox, y + oy, LABEL[k], fontsize=7.4, color=tud.INK, ha='center', va='center', zorder=5)
    path = [CAM['Empty.00%d' % i]['loc'] for i in range(1, 8)]
    a.plot([p[0] for p in path], [p[1] for p in path], '-', color=tud.BLUE_MID, lw=1.0, ls=(0, (4, 2)), zorder=2)
    a.plot([p[0] for p in path], [p[1] for p in path], 'o', color=tud.BLUE_MID, ms=4.5, zorder=4)
    a.text(10.6, 5.3, 'Path camera, positions 1 to 7', fontsize=7.4, color=tud.BLUE_MID, ha='center', va='top')
    a.set_xlim(cx - w / 2 - 0.6, cx + w / 2 + 0.6); a.set_ylim(cy - h / 2 - 0.7, cy + h / 2 + 0.7)
    a.set_aspect('equal'); a.set_xlabel('x (m)'); a.set_ylabel('y (m)')
    a.set_title('(a) top view', fontsize=8.5, loc='left', color=tud.INK)
    a.grid(color=tud.GREY_LIGHT, lw=0.6); a.set_axisbelow(True)
    # (b) side view of the path camera arc
    b.plot([p[0] for p in path], [p[2] for p in path], '-', color=tud.BLUE_MID, lw=1.0, ls=(0, (4, 2)))
    for i, p in enumerate(path):
        b.plot([p[0]], [p[2]], 'o', color=tud.BLUE_MID, ms=5)
        b.text(p[0], p[2] + 0.45, str(i + 1), fontsize=7.4, ha='center', color=tud.INK)
    b.add_patch(Rectangle((cx - w / 2, dom['loc'][2] - dom['dim'][2] / 2), w, dom['dim'][2], fc=tud.BLUE_TINT, ec=tud.BLUE, lw=1.2))
    b.text(cx, dom['loc'][2] + 0.02, 'liquid domain', fontsize=7.4, color=tud.BLUE, ha='center', va='center')
    b.set_xlim(cx - w / 2 - 0.6, cx + w / 2 + 0.6); b.set_ylim(-3.2, 7.2)
    b.set_xlabel('x (m)'); b.set_ylabel('height (m)')
    b.set_title('(b) side view of the path camera positions', fontsize=8.5, loc='left', color=tud.INK)
    b.grid(color=tud.GREY_LIGHT, lw=0.6); b.set_axisbelow(True)
    fig.savefig(os.path.join(OUT, 'figY_reach_layout.png'), dpi=200, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print('wrote', os.path.join(OUT, 'figY_reach_layout.png'))


if __name__ == '__main__':
    main()
