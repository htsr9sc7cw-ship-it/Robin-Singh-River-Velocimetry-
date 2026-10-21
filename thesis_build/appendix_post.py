"""Post-edit of the generated appendix text (called by build_appendix.py): removes stale section columns, adds the supplementary
tables, writes the complete result-source table and fixes the counts of the diagram scripts."""
import json, os, re
R = os.path.dirname(os.path.abspath(__file__))
FILES = {  # result file(s) behind tables whose caption does not name one
    '3.2': '`rerender/camera_to_scene.csv`, `ptv/scene_visual_motion_farneback.csv`', '4.1': '`ptv/derive_ptv_params.py`, `v2_project/ptv_params_v2.csv`',
    '4.3': '`finetune/PREREGISTRATION_strategies.md`', 'met': '`v2_project/compare_v2.py`', 'clear': '`results/three_way_v2.csv`',
    '5.2': '`results/three_way_v2_with_fseed.csv`', '5.3': '`results/three_way_v2_with_fseed.csv`', '5.4': '`results/three_way_v2_with_fseed.csv`',
    '5.5': '`ptv/out_ptv/*/logfileImgSpace.txt`, `results/cascade_corrected.csv`', '5.6': '`results/lk_sweep_v2.csv`', '5.7': '`results/speed_ladder_v2.csv`',
    '5.10': '`results/three_way_v3_k2.csv`', 'pred': '`finetune/PREREGISTRATION_finetune.md`, `finetune/PREREGISTRATION_strategies.md`',
    '5.8': '`finetune/PREREGISTRATION_finetune.md`, `finetune/PREREGISTRATION_strategies.md`', '5.9': '`results/pips_reinit_pilot.csv`',
    '5.11': '`results/finetune_v3.csv`', '5.12': '`results/finetune_v3.csv`', '5.13': '`results/strategies_v3.csv`, `results/stats_strategies_ratio_h15.md`',
    '5.14': '`results/velocity_field_heldout_v3.csv`', '5.14b': '`results/s6_heldout_v3.csv`', '5.15': '`results/surfmove_headline_v3.csv`, `results/tapvid_surfmove_v3.csv`, `results/velocity_field_surfmove_v3.csv`',
    '5.17': '`finetune/results_davis/*_S32.csv`', '6.1': 'derived from the tables of Chapter 5', '3.1': '`ptv/scene_visual_motion_farneback.csv`', 'gtrules': '`FIXLOG.md` (entries V2-1, v3.1, v3.2)',
    '2.1': 'the cited works (Chapter 2)', '1.1': '`figT_route_map.png`'}
EXPL = {
 '5.8': 'Table {T:5.8} lists every prediction as it was locked, the number found and the outcome. Sect. 5.5 sums the outcomes up: of the 42 predictions, 19 were confirmed, 16 were not confirmed, 4 split and 3 were not tested or not informative.',
 '5.9': 'Table {T:5.9} gives the ratio and the direction agreement of every re-tracking setting on the four pilot variants (Sect. 5.3.2). For the pre-trained network, re-tracking in every frame at 256 px is the best setting, and no setting reaches the skill threshold.',
 '5.14b': 'Table {T:5.14b} gives S6 on each held-out variant, in every way of running it and at the two evaluation scales (Sect. 5.3.6). The headline numbers of S6 come from the fresh-seed mode D4 at 256 px.',
 '3.1': 'Table {T:3.1} describes the 15 scenes of the original original dataset (Sect. 3.3). That dataset showed no motion in the images (Sect. 3.6), so none of its tracker results is used in this thesis.',
 'gtrules': 'Table {T:gtrules} lists the rules that were tried for turning the simulated particles into a ground-truth field. Sect. 3.6 describes the final rule v3.2.'}
FILES.update({'f31': '`ptv/derive_ptv_params.py`, `v2_project/ptv_params_v2.csv`', 'f32': '`finetune/PREREGISTRATION_strategies.md`', 'f41': '`rerender/camera_to_scene.csv`',
 'f52': '`results/three_way_v2_with_fseed.csv`', 'f53': '`results/three_way_v2_with_fseed.csv`', 'f54': '`results/three_way_v2_with_fseed.csv`', 'fclear': '`results/three_way_v2.csv`', 'f56': '`results/lk_sweep_v2.csv`', 'f57': '`results/speed_ladder_v2.csv`',
 'f510': '`results/three_way_v3_k2.csv`', 'f511': '`results/finetune_v3.csv`', 'f512': '`results/finetune_v3.csv`', 'f513': '`results/strategies_v3.csv`, `results/s6_heldout_v3.csv`', 'f514': '`results/velocity_field_heldout_v3.csv`, `results/velocity_field_strategies_v3.csv`',
 'f515': '`finetune/results_davis/*_S32.csv`', 'f516': '`results/surfmove_headline_v3.csv`, `results/tapvid_surfmove_v3.csv`, `results/velocity_field_surfmove_v3.csv`', 'glance': '`results/surfmove_headline_v3.csv`, `results/velocity_field_surfmove_v3.csv`',
 '5.13': '`results/strategies_v3.csv`, `results/s6_heldout_v3.csv`, `finetune/results_davis/*_S32.csv`', '5.15': '`results/surfmove_headline_v3.csv`, `results/velocity_field_surfmove_v3.csv`', '5.10': '`results/three_way_v3_k2.csv`'})
EXPL.update({
 'f31': 'Table {T:f31} lists every parameter of the four released sets and the rule of this thesis. Table {T:4.1} in Sect. 4.3 shows the six parameters that differ most.',
 'f32': 'Table {T:f32} adds the clips and the learning-rate schedule of every strategy to Table {T:4.3} in Sect. 4.4.',
 'f41': 'Table {T:f41} adds the 95th percentile of the speed, the mean grey level and the number of features to Table {T:3.2} in Sect. 3.3.',
 'f52': 'Table {T:f52} adds the sub-steps, the share of points within 8 px and the share of tracks following to Table {T:5.2} in Sect. 5.4.1, and the run with feature seeds, which gives the same result as the grid run within 0.02.',
 'f53': 'Table {T:f53} gives the members of each speed group and all metrics. Table {T:5.3} in Sect. 5.4.2 shows the ratio only.',
 'f54': 'Table {T:f54} adds the direction agreement to Table {T:5.4} in Sect. 5.4.3.',
 'fclear': 'Table {T:fclear} adds the clear high-angle view and the GUI defaults to Table {T:clear} in Sect. 5.4.4.',
 'f56': 'Table {T:f56} adds the direction agreement to Table {T:5.6} in Sect. 5.2.',
 'f57': 'Table {T:f57} adds the direction agreement to Table {T:5.7} in Sect. 5.2.',
 'f510': 'Table {T:f510} gives dense and sparse tracers separately and the number of sub-steps for Table {T:5.10} in Sect. 5.3.2.',
 'f511': 'Table {T:f511} gives the ratio of the fine-tuned model and of the other methods on every held-out variant (Sect. 5.3.4).',
 'f512': 'Table {T:f512} gives the medians of all metrics over the ten held-out variants (Sect. 5.3.4).',
 'f513': 'Table {T:f513} gives the ratio of every strategy on every held-out variant. Table {T:5.13} in Sect. 5.3.5 shows the medians.',
 'f514': 'Table {T:f514} gives the per-track and field metrics of the strategies (Sect. 5.3.5). The bias grows with speed, and NCC covers less than half of the water.',
 'f515': 'Table {T:f515} gives δ~avg~, survival and the median error of the reference weights and of every retrained checkpoint (Sect. 5.3.7).',
 'f516': 'Table {T:f516} adds seven measures to the headline Table {T:5.15} in Sect. 5.4.5.'})
def chapter_captions():
    out = []
    for f in ['n1_introduction.md', 'n2_literature.md', 'n4_study_data.md', 'n3_methodology.md', 'n5_results.md', 'n6_discussion.md']:
        for m in re.finditer(r'(?m)^\*\*(Table|Figure) \{([FT]):([^}]+)\}\*\*(.*)$', open(os.path.join(R, f)).read()):
            out.append((m.group(1), m.group(2), m.group(3), m.group(4)))
    return out
def apply(A):
    moved = json.load(open(os.path.join(R, 'moved_tables.json')))
    ORDER = ['f31', 'f32', '3.1', 'f41', 'gtrules', 'f52', 'f53', 'f54', 'fclear', 'f56', 'f57', '5.9', 'f510', '5.8', 'f511', 'f512', 'f513', 'f514', '5.14b', 'f516', 'f515']
    _rank = lambda k: ORDER.index(k.split(':', 1)[1]) if k.split(':', 1)[1] in ORDER else 99
    moved = dict(sorted(moved.items(), key=lambda kv: _rank(kv[0])))
    KEEP = {'f53', 'fclear', 'f513', 'f515', 'f516', '5.8', 'f511'}
    moved = {k: v for k, v in moved.items() if k.split(':', 1)[1] in KEEP}
    lines = A.split('\n'); out = []; strip = False
    for l in lines:
        if l.startswith('|') and re.search(r'\| sect\. \|$', l): strip = True
        if strip and l.startswith('|'):
            l = re.sub(r'\|[^|]*\|$', '|', l)
        elif strip: strip = False
        out.append(l)
    A = '\n'.join(out)
    A = A.replace('register, 17 Sept. 12:00', 'register')
    A = A.replace('(Appendix B.2, A9)', '(change A9 above)')
    A = A.replace('(Appendix B, FIXLOG\nentries F1–F8)', '(FIXLOG\nentries F1–F8)')
    A = A.replace('an audit re-derived all 32\nrows of the parameter file from the frames and the fields with independent code and found', 'all 32\nrows of the parameter file were re-derived from the frames and the fields with separate code and are identical')
    a = A.index('## A.4 Result Sources'); b = A.index('## A.5 Diagram Scripts')
    rows = []
    for kind, tag, key, cap in chapter_captions():
        files = re.findall(r'`((?:results|finetune|fig|ptv|rerender|v2_project|thesis)[^`]*\.(?:csv|txt|png|md|py|pth))`', cap)
        f = ', '.join('`%s`' % x for x in files[:3]) if files and tag == 'F' else FILES.get(key)
        if f is None and files: f = ', '.join('`%s`' % x for x in files[:3])
        rows.append('| %s {%s:%s} | %s |' % (kind, tag, key, f or '–'))
    rows += ['| Table {T:defects} | `logs` (fix log) |']
    for k in moved:
        key = k.split(':', 1)[1]; rows.append('| Table {T:%s} | %s |' % (key, FILES.get(key, '–')))
    sec = ['## A.4 Result Sources and Supplementary Tables', '', '### A.4.1 Result Sources', '',
           'The file behind every table and figure of the thesis is listed in Table {T:src}. The scripts that produce the files are listed in Table {T:scripts}, and `thesis/REPRODUCE.md` gives the command for each table.', '',
           '**Table {T:src}** Result file behind each table and figure', '', '| Table or figure | File |', '|---|---|'] + rows + ['',
           '### A.4.2 Supplementary Tables', '', 'The tables below give the full results behind the tables of the chapters. Each is referred to from the section named in its explanation.', '']
    for k, blocks in moved.items():
        key = k.split(':', 1)[1]
        sec += list(blocks) + ['', EXPL.get(key, ''), '']
    A = A[:a] + '\n'.join(sec) + '\n' + A[b:]
    _d = A[A.index('**Table {T:diag}**'):]
    nd = len([l for l in _d.split('\n') if l.startswith('| Figure {F:')])
    words = {11: 'Eleven', 12: 'Twelve', 13: 'Thirteen', 14: 'Fourteen', 15: 'Fifteen', 16: 'Sixteen', 17: 'Seventeen', 18: 'Eighteen', 19: 'Nineteen'}
    nw = {11: 'eleven', 12: 'twelve', 13: 'thirteen', 14: 'fourteen', 15: 'fifteen', 16: 'sixteen', 17: 'seventeen', 18: 'eighteen', 19: 'nineteen'}
    A = A.replace('Seventeen of the nineteen scripts', '%s of the %s scripts' % (words.get(nd - 1, str(nd - 1)), nw.get(nd, str(nd))))
    A = A.replace('Two scripts draw schematics of the design of the study and show no result: Figure {F:method} (the workflow) and Figure {F:4.3} (the deployment modes). They draw the settings of the study, such as 48-frame blocks and a restart every 2 frames.',
                  'One script draws a schematic of the design of the study and shows no result: Figure {F:4.3} (the deployment modes). It draws the settings of the study, such as 48-frame blocks and a restart every 2 frames.')
    A = A.replace('Every diagram of Chapters 1, 4, 5 and 6 is drawn', 'Every diagram of Chapters 1, 4 and 5 is drawn')
    return A
