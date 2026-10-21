import re
t=open('05_results_draft1.m.md').read()
parts=re.split(r'(?m)^## (\d+\.\d+) .*$',t)
sec={parts[i]:parts[i+1] for i in range(1,len(parts),2)}
sec['5.18']=sec['5.18'].split('## Sources of the Numbers')[0]
def body(k): return sec[k].strip('\n')
lead={
'5.2':"**Aim.** To find out whether either tracker follows the water on the 28 muddy variants. **Approach.** Both trackers were run on the static-surface renders and scored by the same program against the ground truth. **Finding.** Only the cross-correlation mode of FlowVelo (NCC) follows the water: its median ratio is 0.62 and it has skill (ratio below 0.8) on 23 of 28 variants. The pre-trained PIPs++ has a median ratio of 0.99 and the Lucas–Kanade mode (LK) of 0.97.",
'5.3':"**Aim.** To find out where FlowVelo loses its tracks and at which speed each tracking mode breaks. **Approach.** The filter cascade was analysed track by track, the pyramid depth of LK was varied, and the same simulation was replayed at half and quarter speed (speed ladder). **Finding.** The minimum-count filter removes 93–99 % of the tracked features. A defect in the direction function removes a further 20–29 % of the tracks. One more pyramid level brings LK to the level of NCC on the 14–24 px/frame views. NCC breaks between 22 and 47 px/frame on the Low_1 camera.",
'5.4':"**Aim.** To test whether the failure of the pre-trained PIPs++ is an artefact of the way it was driven or tested. **Approach.** Four things were changed one at a time: the seed positions, the working resolution, the re-tracking interval and the surface texture. FlowVelo was given the same feature cadence. **Finding.** None of these changes gives the pre-trained network skill. Re-tracking every 2 frames lowers its ratio on 26 of 28 variants, by a median of only 0.03, and the speed ratio rises from 0.04 to 0.09. The cadence is nearly irrelevant for FlowVelo (NCC 0.62 against 0.64).",
'5.5':"**Aim.** To compare every prediction that was fixed before the runs with what was found. **Approach.** Each prediction of the registers (Sect. 3.6) was scored against its refutation criterion. **Finding.** Many predictions failed. The table below lists all of them, and the text explains the cases that matter for the conclusions.",
'5.6':"**Aim.** To answer RQ2: which retraining strategy gives the best tracker on unseen camera views for a fixed budget? **Approach.** The reference weights were fine-tuned with five strategies under one budget and scored on ten held-out variants. The final model S6 was chosen by the rule fixed in advance. **Finding.** The four strategies that start from the published weights end within 0.06 of each other (median ratio₁₅ 0.69–0.75, NCC 0.62). Training from scratch has no skill (1.04). S6 reaches 0.69 and has skill on 8 of the 10 held-out variants.",
'5.7':"**Aim.** To compare pre-trained PIPs++, retrained PIPs++ and FlowVelo on the final, most realistic data (RQ1 and RQ3). **Approach.** All four methods were run on the moving-surface frames of the 28 muddy variants and scored by the same program. **Finding.** The pre-trained model has no skill on any variant (median ratio 0.93). The retrained model S6 has skill on 24 of 28 variants (0.69), covers 99 % of the water and reads the flow about 42 % too slow (speed ratio 0.71). NCC is more accurate (0.49, speed ratio 1.00, bias −10 %) and has skill on 24 of 28 variants, but it covers only 56 % of the water. LK has skill on 12 variants (0.81).",
'5.8':"**Aim.** To measure what retraining costs in general tracking ability (RQ3). **Approach.** Every checkpoint was tested on the 30 videos of TAP-Vid-DAVIS with identical settings. **Finding.** The reference weights reach δ_avg 66.4, and S6 reaches 58.7, a loss of 12 %. Training from scratch gives 11.9.",
}
intro='''# 5 Results

This chapter reports what was found. It follows the three objectives of the task and the research questions of Chapter 1. Table {T:obj} shows which sections answer which question. Each section starts with its aim, the approach and the main finding, and the details follow.

**Table {T:obj}** Objectives, research questions and the sections that answer them.

| Objective | Research question | Sections |
|---|---|---|
| Data check | Is the ground truth accurate enough to score the trackers? | 5.1 |
| 1 Pre-trained PIPs++ | RQ1: does it recover the true motion of moving water, and how does it compare with FlowVelo? | 5.2–5.5 |
| 2 Retraining strategies | RQ2: which strategy gives the best tracker on unseen camera views? | 5.6 |
| 3 Pre-trained against retrained | RQ3: how do they compare with FlowVelo in different conditions, and what does retraining cost? | 5.7–5.8 |
| All | Summary of the answers | 5.9 |

All numbers in this chapter are read from the files under `v2_project/results/` that were produced by the scoring path of Sect. 3.5; Appendix A.5 lists the file behind every table and figure. Unless stated otherwise, a "variant" is one of the 28 muddy-water variants of the third dataset (14 camera views × {sparse, dense} tracers). The two clear-water camera views are reported in Sect. 5.2.4, because their renders were regenerated on the last day and are not part of the medians in Sects. 5.2.1–5.2.3. All displacements are in native pixels per frame (px/frame) of the 512 × 512 frames (Overview: 1024 × 512). The ratio is the RMSE of the tracked displacement divided by the RMSE of the stay-still baseline at the same points (Eq. 3.1). A ratio of 1 means that a tracker did no better than assuming that nothing moves.
'''
new=[intro]
def add(h,k=None,lk=None):
    new.append('\n'+h+'\n')
    if lk: new.append('\n'+lead[lk]+'\n')
    if k: new.append('\n'+body(k)+'\n')
add('## 5.1 Ground Truth','5.1')
add('## 5.2 Baseline Comparison',None,'5.2')
for hh,k in [('### 5.2.1 Overall','5.2'),('### 5.2.2 Speed Groups','5.3'),('### 5.2.3 Tracer Density','5.4'),('### 5.2.4 Clear Water','5.9')]: add(hh,k)
add('## 5.3 FlowVelo Settings',None,'5.3')
for hh,k in [('### 5.3.1 Filter Cascade','5.5'),('### 5.3.2 Pyramid Depth','5.6'),('### 5.3.3 Speed Ladder','5.7')]: add(hh,k)
add('## 5.4 Controls',None,'5.4')
for hh,k in [('### 5.4.1 Seeding and Surface','5.8'),('### 5.4.2 Re-Tracking','5.12'),('### 5.4.3 Worked Examples','5.10')]: add(hh,k)
add('## 5.5 Predictions','5.11','5.5')
add('## 5.6 Retraining',None,'5.6')
for hh,k in [('### 5.6.1 Fine-Tuning','5.13'),('### 5.6.2 Strategies','5.14'),('### 5.6.3 Final Model','5.15')]: add(hh,k)
add('## 5.7 Moving Water','5.16','5.7')
add('## 5.8 Retention','5.17','5.8')
add('## 5.9 Synthesis','5.18')
out=''.join(new)
open('n5_results.md','w').write(out)
print(len(out.split()),'words')
