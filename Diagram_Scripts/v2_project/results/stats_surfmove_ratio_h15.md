# results/surfmove_headline_v3.csv — ratio_h15 (variants = 28, excluded ['v2_Path3_clear_surfmove_dense', 'v2_Path3_clear_surfmove_sparse', 'v2_high_angle_clear_surfmove_dense', 'v2_high_angle_clear_surfmove_sparse'])

| method | n | median | 95 % CI (bootstrap) |
|---|---|---|---|
| PIPs++ | 2 | 0.924 | [0.862, 0.986] |
| PIPs++_S6_b2_256 | 28 | 0.691 | [0.583, 0.732] |
| PIPs++_b2_256 | 28 | 0.928 | [0.912, 0.941] |
| PTV_tuned_lk_fd2 | 28 | 0.811 | [0.761, 0.861] |
| PTV_tuned_ncc_fd2 | 28 | 0.493 | [0.319, 0.582] |

| A | B | A better | B better | ties | sign-test p |
|---|---|---|---|---|---|
| PIPs++ | PIPs++_S6_b2_256 | 0 | 2 | 0 | 0.500 |
| PIPs++ | PIPs++_b2_256 | 2 | 0 | 0 | 0.500 |
| PIPs++ | PTV_tuned_lk_fd2 | 0 | 2 | 0 | 0.500 |
| PIPs++ | PTV_tuned_ncc_fd2 | 0 | 2 | 0 | 0.500 |
| PIPs++_S6_b2_256 | PIPs++_b2_256 | 28 | 0 | 0 | 0.000 |
| PIPs++_S6_b2_256 | PTV_tuned_lk_fd2 | 22 | 6 | 0 | 0.004 |
| PIPs++_S6_b2_256 | PTV_tuned_ncc_fd2 | 7 | 21 | 0 | 0.013 |
| PIPs++_b2_256 | PTV_tuned_lk_fd2 | 1 | 27 | 0 | 0.000 |
| PIPs++_b2_256 | PTV_tuned_ncc_fd2 | 1 | 27 | 0 | 0.000 |
| PTV_tuned_lk_fd2 | PTV_tuned_ncc_fd2 | 3 | 25 | 0 | 0.000 |
