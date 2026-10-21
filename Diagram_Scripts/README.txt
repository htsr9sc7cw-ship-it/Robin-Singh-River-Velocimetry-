DIAGRAM SCRIPTS OF THE THESIS
=============================
Every diagram of the thesis is computed by its own Python script from the result files of the real experiments (the tables written by the scoring program compare_v2.py from the real tracker runs, and the tracker output files themselves). Nine of the 13 diagrams of the thesis (Sect. A.5) compute every number they draw from those files; no result is typed into them. Four (fig_3_01_methodology.py, fig_3_07_ptv_pipeline.py, fig_3_08_ratio_concept.py, fig_3_03_deployment_modes.py = Figures 4.1, 4.2, 4.4, 4.5) are schematics or illustrations of the design of the study and show no result. This folder holds the scripts,
the result tables they read, and the thesis pictures to compare with.

EASIEST: double-click Run_all_diagrams.command (opens Terminal and runs everything).

ONE COMMAND (draws all 29 scripts fig_*.py and compares the pictures with the 20 thesis pictures):
    cd ~/Desktop/Diagram_Scripts
    /opt/anaconda3/bin/python3 run_all_diagrams.py
In PyCharm: open this folder, press the green Run button next to "Run all diagrams" (top right).
Each picture is reported as IDENTICAL (same pixels), SAME (same picture, tiny rendering differences) or DIFFERENT.  New pictures appear in v2_project/results/figures/.

ONE DIAGRAM ONLY (example: Figure "fine-tuned PIPs++ on the held-out views"):
    /opt/anaconda3/bin/python3 v2_project/figure_scripts/fig_5_11_finetune_heldout.py
In PyCharm: right-click the file > Run.

Which script draws which diagram: see Sect. A.5 of the thesis.
Interpreter: Anaconda base Python 3.13 (numpy 2.3.5, pandas 2.3.3, matplotlib 3.10.6). Three diagrams that draw tracks on a frame
(fig_5_10, fig_5_12, fig_5_17) need opencv and OpenEXR; the runner finds them in the conda environment "pips2".
On the reference computer the pictures are identical or the same. On another computer, fonts and library versions can change single pixels or the size by a pixel; the runner then reports SAME. The numbers drawn are always the same.
