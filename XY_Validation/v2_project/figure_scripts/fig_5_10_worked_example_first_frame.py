"""Figure 5.10  Worked example, first frame: Path4 dense, ground truth, PTV NCC, PTV LK and pre-trained PIPs++.
Output: results/figures/figF_example_v2_Path4_dense.png
Run with the pips2 interpreter:  /opt/anaconda3/envs/pips2/bin/python fig_5_10_worked_example_first_frame.py"""
from worked_example import worked_example

worked_example('v2_Path4_dense', '', 'figF_example_v2_Path4_dense.png', with_lk=True)
