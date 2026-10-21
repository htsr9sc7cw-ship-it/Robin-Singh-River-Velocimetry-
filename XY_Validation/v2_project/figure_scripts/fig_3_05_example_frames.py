"""Figure (example frames) of the final dataset.
Output: results/figures/figX_example_frames.png      Run:  python fig_3_05_example_frames.py
Six first frames (simulation frame 80) of the rendered scenes: two tracer densities of one view, a fast and a wide view, and the two water materials of one view.
The mean grey level and the water share are measured from the images and the ground truth files themselves; no number is typed in by hand."""
import os
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

import tud_style as tud

HERE = os.path.dirname(os.path.abspath(__file__))
XY = os.path.dirname(HERE)
OUT = os.path.join(XY, 'results', 'figures')
DATA = os.path.join(XY, 'Vectors_and_Images')
tud.apply()

PANELS = [('v2_Path4_dense', 'Path4, dense tracers'), ('v2_Path4_sparse', 'Path4, sparse tracers'),
          ('v2_Low_1_dense', 'Low_1, dense tracers'), ('v2_Overview_dense', 'Overview, dense tracers'),
          ('v2_Path3_dense', 'Path3, muddy water'), ('v2_Path3_clear_dense', 'Path3, clear water')]


def main():
    fig = plt.figure(figsize=(7.2, 5.6))
    gs = fig.add_gridspec(2, 3, wspace=0.04, hspace=0.16, left=0.01, right=0.99, top=0.95, bottom=0.01, width_ratios=[1, 1, 1])
    for i, (scene, label) in enumerate(PANELS):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        im = Image.open(os.path.join(DATA, scene, 'images', '0080.png')).convert('RGB')
        arr = np.asarray(im)
        grey = float(arr.mean())
        ax.imshow(arr, aspect='equal')
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_anchor('N')              # panels of other aspect ratio (d: 2:1) sit directly under their title, not centred in the cell
        for sp in ax.spines.values():
            sp.set_color(tud.BLUE); sp.set_linewidth(1.0)
        ax.set_title('(%s) %s' % ('abcdef'[i], label), fontsize=8.0, color=tud.INK, pad=3)
        ax.text(0.03, 0.04, 'mean grey level %.0f' % grey, transform=ax.transAxes, fontsize=7.0, color='white', va='bottom',
                bbox=dict(boxstyle='round,pad=0.2', fc=tud.BLUE, ec='none', alpha=0.85))
        print(scene, 'mean grey %.1f' % grey, im.size)
    fig.savefig(os.path.join(OUT, 'figX_example_frames.png'), dpi=200, facecolor='white')
    plt.close(fig)
    print('wrote', os.path.join(OUT, 'figX_example_frames.png'))


if __name__ == '__main__':
    main()
