# results/strategies_v3.csv — ratio_h15 (variants = 10, excluded ['v2_Path2_dense'])

| method | n | median | 95 % CI (bootstrap) |
|---|---|---|---|
| PIPs++_b2_256 | 10 | 0.998 | [0.978, 1.000] |
| PIPs++_ft3000_b2_256 | 10 | 0.717 | [0.522, 0.857] |
| PIPs++_S2_b2_256 | 10 | 0.712 | [0.637, 0.820] |
| PIPs++_S3_b2_256 | 10 | 0.748 | [0.567, 0.861] |
| PIPs++_S3_r48_256 | 10 | 0.685 | [0.377, 0.839] |
| PIPs++_S4_b2_256 | 10 | 0.706 | [0.626, 0.856] |
| PIPs++_S5_b2_256 | 10 | 1.045 | [0.996, 1.299] |
| PTV_tuned_ncc_fd2 | 10 | 0.622 | [0.289, 0.837] |
| PTV_tuned_lk_fd2 | 10 | 0.992 | [0.879, 1.000] |

| A | B | A better | B better | ties | sign-test p |
|---|---|---|---|---|---|
| PIPs++_b2_256 | PIPs++_ft3000_b2_256 | 0 | 10 | 0 | 0.002 |
| PIPs++_b2_256 | PIPs++_S2_b2_256 | 0 | 10 | 0 | 0.002 |
| PIPs++_b2_256 | PIPs++_S3_b2_256 | 0 | 10 | 0 | 0.002 |
| PIPs++_b2_256 | PIPs++_S3_r48_256 | 0 | 10 | 0 | 0.002 |
| PIPs++_b2_256 | PIPs++_S4_b2_256 | 0 | 10 | 0 | 0.002 |
| PIPs++_b2_256 | PIPs++_S5_b2_256 | 8 | 2 | 0 | 0.109 |
| PIPs++_b2_256 | PTV_tuned_ncc_fd2 | 1 | 9 | 0 | 0.021 |
| PIPs++_b2_256 | PTV_tuned_lk_fd2 | 3 | 7 | 0 | 0.344 |
| PIPs++_ft3000_b2_256 | PIPs++_S2_b2_256 | 6 | 4 | 0 | 0.754 |
| PIPs++_ft3000_b2_256 | PIPs++_S3_b2_256 | 8 | 2 | 0 | 0.109 |
| PIPs++_ft3000_b2_256 | PIPs++_S3_r48_256 | 2 | 8 | 0 | 0.109 |
| PIPs++_ft3000_b2_256 | PIPs++_S4_b2_256 | 6 | 4 | 0 | 0.754 |
| PIPs++_ft3000_b2_256 | PIPs++_S5_b2_256 | 10 | 0 | 0 | 0.002 |
| PIPs++_ft3000_b2_256 | PTV_tuned_ncc_fd2 | 3 | 7 | 0 | 0.344 |
| PIPs++_ft3000_b2_256 | PTV_tuned_lk_fd2 | 9 | 1 | 0 | 0.021 |
| PIPs++_S2_b2_256 | PIPs++_S3_b2_256 | 5 | 5 | 0 | 1.000 |
| PIPs++_S2_b2_256 | PIPs++_S3_r48_256 | 4 | 6 | 0 | 0.754 |
| PIPs++_S2_b2_256 | PIPs++_S4_b2_256 | 2 | 8 | 0 | 0.109 |
| PIPs++_S2_b2_256 | PIPs++_S5_b2_256 | 10 | 0 | 0 | 0.002 |
| PIPs++_S2_b2_256 | PTV_tuned_ncc_fd2 | 3 | 7 | 0 | 0.344 |
| PIPs++_S2_b2_256 | PTV_tuned_lk_fd2 | 9 | 1 | 0 | 0.021 |
| PIPs++_S3_b2_256 | PIPs++_S3_r48_256 | 2 | 8 | 0 | 0.109 |
| PIPs++_S3_b2_256 | PIPs++_S4_b2_256 | 6 | 4 | 0 | 0.754 |
| PIPs++_S3_b2_256 | PIPs++_S5_b2_256 | 10 | 0 | 0 | 0.002 |
| PIPs++_S3_b2_256 | PTV_tuned_ncc_fd2 | 3 | 7 | 0 | 0.344 |
| PIPs++_S3_b2_256 | PTV_tuned_lk_fd2 | 9 | 1 | 0 | 0.021 |
| PIPs++_S3_r48_256 | PIPs++_S4_b2_256 | 6 | 4 | 0 | 0.754 |
| PIPs++_S3_r48_256 | PIPs++_S5_b2_256 | 10 | 0 | 0 | 0.002 |
| PIPs++_S3_r48_256 | PTV_tuned_ncc_fd2 | 3 | 7 | 0 | 0.344 |
| PIPs++_S3_r48_256 | PTV_tuned_lk_fd2 | 9 | 1 | 0 | 0.021 |
| PIPs++_S4_b2_256 | PIPs++_S5_b2_256 | 10 | 0 | 0 | 0.002 |
| PIPs++_S4_b2_256 | PTV_tuned_ncc_fd2 | 3 | 7 | 0 | 0.344 |
| PIPs++_S4_b2_256 | PTV_tuned_lk_fd2 | 9 | 1 | 0 | 0.021 |
| PIPs++_S5_b2_256 | PTV_tuned_ncc_fd2 | 1 | 9 | 0 | 0.021 |
| PIPs++_S5_b2_256 | PTV_tuned_lk_fd2 | 2 | 8 | 0 | 0.109 |
| PTV_tuned_ncc_fd2 | PTV_tuned_lk_fd2 | 9 | 1 | 0 | 0.021 |
