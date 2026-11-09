# SPECTRUM ICLR2027 rebuttal — completed local experiment results (2026-11-09)

Completed cases: 40. Receipts under `receipts/`, final metrics under `metrics/`.

| case | kind | model | method | pass@1 | pass@64 | correct/samples |
|---|---|---|---|---|---|---|
| c01 | train | qwen1.5b | spectral_soft | 0.4024 | 0.7240 | 12878/32000 |
| c02 | train | qwen1.5b | random_soft | 0.3925 | 0.7300 | 12559/32000 |
| c03 | train | qwen1.5b | isotropic_soft | 0.3960 | 0.7260 | 12673/32000 |
| c04 | train | qwen1.5b | matched_blend | 0.4206 | 0.7120 | 13459/32000 |
| c05 | train | qwen1.5b | plain | 0.4179 | 0.7060 | 13373/32000 |
| c06 | train | qwen1.5b | plain | 0.4133 | 0.7160 | 13227/32000 |
| c07 | train | qwen1.5b | spectral_soft | 0.4006 | 0.7280 | 12820/32000 |
| c08 | train | qwen1.5b | plain | 0.4159 | 0.7020 | 13308/32000 |
| c09 | train | qwen1.5b | spectral_soft | 0.4009 | 0.7120 | 12829/32000 |
| c10 | train | qwen1.5b | plain | 0.2095 | 0.4540 | 6704/32000 |
| c11 | train | qwen1.5b | spectral_soft | 0.0904 | 0.2940 | 2892/32000 |
| c12 | train | qwen1.5b | spectral_soft | 0.4136 | 0.7180 | 13236/32000 |
| c13 | train | qwen1.5b | spectral_soft | 0.3896 | 0.7280 | 12467/32000 |
| c14 | train | deepseek6.7b | plain | 0.4744 | 0.7260 | 15180/32000 |
| c15 | train | deepseek6.7b | spectral_soft | 0.4679 | 0.7240 | 14974/32000 |
| c18 | train | qwen3b | plain | 0.5062 | 0.7320 | 16199/32000 |
| c19 | train | qwen3b | spectral_soft | 0.4989 | 0.7200 | 15965/32000 |
| c20 | decoder | - | cool | 0.4291 | 0.6900 | 13731/32000 |
| c20 | decoder | - | cool | 0.4207 | 0.7040 | 13461/32000 |
| c21 | decoder | - | warm | 0.3951 | 0.7240 | 12643/32000 |
| c21 | decoder | - | warm | 0.3757 | 0.7220 | 12021/32000 |
| c22 | decoder | - | ssd_recipe | 0.3740 | 0.7300 | 11968/32000 |
| c22 | decoder | - | ssd_recipe | 0.3472 | 0.7260 | 11110/32000 |
| c23 | train | qwen1.5b | spectral_soft | 0.4053 | 0.7240 | 12971/32000 |
| c24 | train | qwen1.5b | spectral_soft | 0.4150 | 0.7160 | 13281/32000 |
| c27 | train | qwen1.5b | spectral_soft | 0.4028 | 0.7260 | 12889/32000 |
| c28 | train | qwen1.5b | plain | 0.3908 | 0.7300 | 12505/32000 |
| c29 | train | qwen1.5b | plain | 0.3593 | 0.7240 | 11497/32000 |
| c30 | train | qwen1.5b | ssd | 0.3592 | 0.7200 | 11494/32000 |
| c31 | train | qwen1.5b | spectral_soft | 0.4006 | 0.7280 | 12818/32000 |
| c32 | interpolate | - | plain | 0.3927 | 0.7340 | 12567/32000 |
| c33 | interpolate | - | plain | 0.4045 | 0.7100 | 12945/32000 |
| c34 | interpolate | - | spectral_soft | 0.3857 | 0.7360 | 12344/32000 |
| c35 | interpolate | - | spectral_soft | 0.3928 | 0.7260 | 12569/32000 |
| c36 | train | qwen1.5b | plain | 0.4147 | 0.7120 | 13269/32000 |
| c44 | train | qwen1.5b | plain | 0.2066 | 0.4940 | 6612/32000 |
| c45 | train | qwen1.5b | spd_hard | 0.4165 | 0.7060 | 13329/32000 |
| c46 | decoder | - | nucleus_tight | 0.4282 | 0.6860 | 13703/32000 |
| c46 | decoder | - | nucleus_tight | 0.4222 | 0.7020 | 13509/32000 |
| c47 | train | qwen1.5b | plain | 0.4287 | 0.7040 | 13718/32000 |
