| strategy | ratio₁₅ | dir. | follow | speed | mean-speed bias % | field RMSE % | coverage | cells within target |
|---|---|---|---|---|---|---|---|---|
| S0 pre-trained | 1.00 | 0.22 | 0.01 | 0.04 | -78 | 117 | 0.92 | 0.01 |
| S1 FT-1 (short clips, 9 views) | 0.72 | 0.83 | 0.71 | 0.86 | -27 | 72 | 1.00 | 0.25 |
| S2 data + augmentation | 0.71 | 0.81 | 0.71 | 0.87 | -31 | 68 | 1.00 | 0.28 |
| S3 long clips (24) | 0.75 | 0.75 | 0.62 | 0.68 | -31 | 87 | 1.00 | 0.22 |
| S3 long clips, long-term mode | 0.69 | 0.75 | 0.63 | 0.77 | -41 | 62 | 1.00 | 0.31 |
| S4 rehearsal (50 % PointOdyssey) | 0.71 | 0.68 | 0.57 | 0.69 | -31 | 82 | 1.00 | 0.22 |
| S5 from scratch | 1.04 | 0.36 | 0.20 | 0.69 | -53 | 97 | 1.00 | 0.02 |
| FlowVelo NCC | 0.62 | 0.89 | 0.75 | 0.98 | -12 | 45 | 0.42 | 0.28 |
| FlowVelo LK | 0.99 | 0.46 | 0.06 | 0.03 | -91 | 102 | 0.79 | 0.01 |
