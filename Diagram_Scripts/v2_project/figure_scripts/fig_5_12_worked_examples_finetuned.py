"""Figure 5.12  Worked examples, fine-tuned model: Path4 dense (left) and Low 1 dense (right), FT-1 re-tracked every 2 frames.
Output: results/figures/figF_example_v2_Path4_dense_ft3000_r2_256.png and figF_example_v2_Low_1_dense_ft3000_r2_256.png
Run with the pips2 interpreter:  /opt/anaconda3/envs/pips2/bin/python fig_5_12_worked_examples_finetuned.py
"""

from worked_example import worked_example

# the two pictures are stacked in the thesis (one figure, two rows): the panel letters run on (a-c, d-f) and each row is tagged
for scene, first, tag in (
    ("v2_Path4_dense", "a", "Top row: Path4, dense"),
    ("v2_Low_1_dense", "d", "Bottom row: Low_1, dense"),
):
    worked_example(
        scene,
        "ft3000_r2_256",
        "figF_example_%s_ft3000_r2_256.png" % scene,
        first_letter=first,
        row_tag=tag,
    )
