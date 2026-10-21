"""Figure 4.3  Processing steps of the PTV implementation (schematic).
Output: results/figures/figZ_ptv_pipeline.png      Run:  python fig_3_07_ptv_pipeline.py
Text from Sect. 4.3 of the thesis (Eltner et al., 2020; Shi and Tomasi, 1994); no numbers are computed here."""
import tud_style as tud
from fig_1_01_route_map import canvas, tbox, save


def pipeline():
    fig, ax = canvas(7.2, 5.6, 72, 56, x0=-1)
    rows = [('1  Detection', ['Shi–Tomasi corners; very dark pixels', 'and crowded clusters are removed']),
            ('2  Tracking', ['NCC: template search, match accepted if γ > 0.9', 'LK: pyramid with two levels (OpenCV maxLevel = 2)']),
            ('3  Consistency check', ['every match is tracked back to the previous frame;', 'it must return to within 1 px of the start']),
            ('4  Filtering', ['six rules: movement per frame (minimum, maximum),', 'track length, steadiness, direction range, main flow']),
            ('5  Output', ['tracks of surface features in px/frame', '(metric velocities need the camera geometry)'])]
    y = 46
    for i, (name, lines) in enumerate(rows):
        tbox(ax, 3, y, 20, [name], h=8, lw=1.6 if i == 4 else 1.4)
        tbox(ax, 27, y, 42, lines, h=8, bold=0, lw=1.0)
        tud.arrow(ax, 23, y + 4, 27, y + 4)
        if i < 4:
            tud.arrow(ax, 13, y, 13, y - 2.2)
        y -= 10.2
    save(fig, 'figZ_ptv_pipeline.png')


if __name__ == '__main__':
    pipeline()
