# Pre-registration: FlowVeloTool PTV on the 15 Blender Elbersdorf scenes

Written 2026-09-11, BEFORE any PTV output exists. Locked. If a prediction below is wrong,
that is a finding, not something to be adjusted after the fact.

## What is being tested
Anette Eltner's FlowVeloTool (python3_version/latest_version, unmodified), run in her
"Stay in image space" mode on the 512x512, 301-frame rendered frames of each scene, with
tracks scored against the Blender vector-pass ground truth by the SAME evaluator that
already scored PIPs++.

## Measured scene properties these predictions are based on (read-only, 2026-09-11)
Speed = ground-truth flow magnitude on the mid-clip frame, water pixels only.
Brightness = grey-level mean of the mid-clip frame. GFTT = cv2.goodFeaturesToTrack count at
her default sensitivity 0.002, minDistance 10.

| scene | mean px/frame | p95 px/frame | grey mean | % px > 100 | GFTT @0.002 | water % |
|---|---|---|---|---|---|---|
| clear high angle | 18.2 | 20.8 | 117 | 94.1 | 90 | 100 |
| clear path3 | 15.8 | 17.7 | 115 | 96.6 | 1453 | 100 |
| Low0 | 25.2 | 34.7 | 71 | 4.9 | 81 | 100 |
| Low1 | 87.2 | 160.5 | 66 | 7.5 | 298 | 100 |
| Low2 | 48.6 | 104.5 | 57 | 3.2 | 923 | 100 |
| Low3 | 30.1 | 64.9 | 69 | 11.5 | 1288 | 100 |
| Low4 | 38.6 | 80.5 | 66 | 3.3 | 146 | 100 |
| Low5 | 98.1 | 147.4 | 69 | 4.7 | 200 | 100 |
| Overview | 11.6 | 13.7 | 51 | 4.3 | 262 | 95.0 |
| Path1 | 19.2 | 28.9 | 95 | 29.7 | 580 | 71.5 |
| Path2 | 15.4 | 20.3 | 59 | 1.8 | 61 | 98.3 |
| Path3 | 15.8 | 17.7 | 50 | 0.0 | 1359 | 100 |
| Path4 | 16.0 | 17.0 | 49 | 0.0 | 1 | 100 |
| Path5 | 15.9 | 18.7 | 51 | 1.1 | 84 | 100 |
| Path6 | 15.5 | 21.3 | 58 | 3.2 | 260 | 98.9 |

## Predictions (falsifiable)

P1. **Her GUI v3 defaults return < 10 final tracks on at least 12 of 15 scenes.**
    Reason: brightness threshold 70 removes most features on the 13 dark scenes; LK with a
    7x7 window and maxLevel=2 cannot follow > ~14 px/frame; max track distance 50 px.

P2. **With per-scene parameters, PTV recovers the mean flow DIRECTION within 10 deg of ground
    truth on the slow, textured scenes**: clear path3, Path3, Low3, Low2. These have >900 GFTT
    features and (except Low2) < 20 px/frame.

P3. **PTV fails (< 50 final tracks, or direction error > 30 deg) on Path4 and Path2** —
    1 and 61 detectable features at default sensitivity; nothing to track regardless of speed.

P4. **PTV fails on Low1 and Low5** even with tuned parameters: p95 speed 147-160 px/frame
    means a feature crosses a 512 px frame in ~4 frames; her minimum-count filter (65 % of
    the tracking length) cannot be met, and shifted search windows leave the frame.

P5. **Where PTV produces final tracks, its median endpoint error is BELOW PIPs++'s** on the
    same scene, because her forward-backward check and filter cascade discard incoherent
    tracks while PIPs++ reports every seed. Corollary: PTV coverage (fraction of 32x32 cells
    with a track) is LOWER than PIPs++'s on every scene.

P6. **PTV's per-track direction spread (circular std) is < 15 deg on every scene where it
    survives filtering**, versus the 103-131 deg already measured for PIPs++. Reason: the
    steadiness filter enforces this by construction — so this is a check that the filter did
    its job, not evidence of tracking skill on its own.

P7. **NCC mode produces fewer final tracks than LK mode on every scene** (correlation > 0.9
    hard-coded, integer positions vs 1 px forward-backward tolerance) but with lower endpoint
    error where it does track.

P8. **The interior-orientation round trip (undistort -> metric_to_pixel) shifts every point by
    exactly -1.0 px in x and y** (algebra from pixel_to_metric / metric_to_pixel). If measured
    otherwise, the algebra in FIXLOG is wrong and must be corrected there first.

P9. **Ordering of the three methods by median endpoint error on scenes where all three have
    output: ground truth (0) < PTV < PIPs++.** If PIPs++ beats PTV on any such scene, that
    scene is reported first in the results.

P10. **Speed ratio (measured / true) for PTV is between 0.9 and 1.1** where it tracks — PTV
     should not show the LSPIV underestimation Tauro et al. (2017) describe. PIPs++'s ratio is
     already known to be uncorrelated with truth (r = -0.08).

## What would falsify the whole approach (stop conditions)
- The known-answer test (a real frame warped by its own GT flow, then tracked) fails to
  recover the mean flow within 1 px and 2 deg -> the driver is wrong. Nothing else is run.
- Path3 direction error > 5 deg with tuned parameters -> parameter derivation is wrong.
