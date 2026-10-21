THESIS KIT   Evaluation of AI-Based Particle Tracking Method for Surface Water Velocity Estimation   (Robin Singh, TU Dresden)

Everything needed to run the scripts of the thesis on one scene (v2_Path4_dense) on any computer, with the real data:
rendered frames, exact ground truth, particles, pre-trained PIPs++ weights and the retrained model (S6), FlowVeloTool, all scripts.

1  Install Miniconda (https://docs.conda.io/en/latest/miniconda.html), open a terminal (Mac: Terminal; Windows: Anaconda Prompt).
2  cd into this folder:               cd "<path>/thesis_kit"
3  once per computer:                 python run.py setup
4  the whole study, 6 to 8 min, with the numbers of the thesis next to the numbers just measured:
                                      python run.py demo
5  any single script of the thesis:   python run.py <name>        (names: python run.py list)

Examples:  python run.py known_answer_eval     python run.py lk_sweep     python run.py train_v3     python run.py rasterise_gt
Tested on macOS (Apple M-series GPU); on a computer without a GPU the same commands run on the CPU, slower.
Not in the kit (too large, on the project drive): the other 31 variants (27 muddy, 4 clear), the Blender fluid cache (about 40 GB), the
TAP-Vid-DAVIS benchmark (2.5 GB). The scripts that need them say so when started.
