"""Print-only clean-up of the scripts printed in Appendix A.6 (used by source_appendix.py and verify_thesis.py)."""
import os


def clean(src, name):
    """Print-only clean-up: placeholder headers, dates, personal references and the path of the author's Python installation.
    Nothing else is changed; the scripts in the digital appendix are the ones that were run."""
    import re as _re
    src = src.replace("'her test_run: first 20 frames only'", "'test_run of the tool: first 20 frames only'").replace("'her savePlotData (slow)'", "'savePlotData of the tool (slow)'").replace("os.path.expanduser('~/anaconda3/envs/pips2/bin/python'), os.path.expanduser('~/miniconda3/envs/pips2/bin/python')", "os.path.expanduser('~/anaconda3/envs/pips2/bin/python')").replace("'/opt/anaconda3/envs/pips2/bin/python',", '')
    src = _re.sub(r'(?m)^(Thesis section|Inputs|Outputs)\s*:.*\n', '', src)
    src = _re.sub(r'""" ?\n\n+', '"""\n', src)
    src = _re.sub(r'\s*\[?\(?20\d\d-\d\d-\d\d\]?\)?', '', src)
    src = src.replace("'/opt/anaconda3/envs/pips2/bin/python'", 'sys.executable').replace("/opt/anaconda3/envs/pips2/bin/python ", 'python ').replace("/opt/anaconda3/envs/flowvelo/bin/python ", 'python ').replace("/opt/anaconda3/bin/python ", 'python ').replace("'/opt/anaconda3/bin/python'", 'sys.executable')
    src = src.replace("Run Anette Eltner's FlowVeloTool", 'Run FlowVeloTool (Eltner et al., 2020)')
    for a_, b_ in [('Her source', "The tool's source"), ('Her own precedent', "The authors' own precedent"), ('her GUI', 'the GUI'), ('Her GUI', 'The GUI'), ("her paper's method", "the paper's method"),
                   ('her own plots', 'its own plots'), ('her function option', 'the function option'), ('her backward check', 'its backward check'), ('her EstimateVelocity', 'the EstimateVelocity'),
                   ('her code', "the tool's code"), ('Her code', "The tool's code"), ('Her FeatureTracking', 'FeatureTracking'), ('her draw_tracks', 'draw_tracks'), ('her file', "the tool's file"),
                   ('(hers)', '(tool)'), ('her read_imgs_folder', 'read_imgs_folder'), ('her logfileImgSpace.txt', 'the logfileImgSpace.txt'), ('her files', "the tool's files"),
                   ('her option', 'the option'), ('Her other filters', 'The other filters'), ('her detection option', 'the detection option'), ('is hers', 'is the tool\'s'), ('as she computed them', 'as the tool computed them'),
                   ('Body copied from hers', 'Body copied from the tool'), ('call sequence is\nhers', 'call sequence is\nthe tool\'s'), ('and the outputs are her files', "and the outputs are the tool's files"),
                   ('Her FilterTracks', 'FilterTracks'), ('her FilterTracks', 'FilterTracks'), ("her paper's", "the paper's"), ('her tracker', "the tool's tracker")]:
        src = src.replace(a_, b_)
    src = _re.sub(r'\bher\b', "the tool's", src); src = _re.sub(r'\bHer\b', "The tool's", src); src = _re.sub(r'\bhers\b', "the tool's", src)
    src = src.replace("help='velocity-attribute calibration: front speed 0.281 m/frame vs attribute 0.205 (FIXLOG S4)'", "help='velocity-attribute calibration (Sect. 4.4)'")
    src = _re.sub(r'\(measured: 0\.075 m/frame = 1\.9 m/s at fps 25, matching the visual motion\); ', '; ', src)
    src = _re.sub(r'n_offwater = \(\n\s+int\(\(mask & ~keep\)\[1:\]\.sum\(\) - \(~np\.isfinite\(dx\) & mask\)\[1:\]\.sum\(\)\)\n\s+if False\n\s+else int\(n_expected - keep\.sum\(\)\)\n\s+\)', 'n_offwater = int(n_expected - keep.sum())', src)
    if name == 'run_all_diagrams.py':
        k = src.index('"""', 3) + 3
        src = src[:k].replace('\\n', '\n') + src[k:]
    return src
