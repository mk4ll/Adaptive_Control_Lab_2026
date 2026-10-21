# extras_lab6rest - HARDWARE run 20261021_142835


## Lab I.6: remaining runs and sigma-modification toward nominal values

Same design as Lab I.6 (wn = 1.5 rad/s, zeta = 1, gamma = 5.0, dead-zone inverse 61.7 PWM, model results/rig/model.json). Ideal: k1* = -0.398, k2* = 0.805, l* = 0.398.

`sigma_nominal`: the estimates START at the nominal model values and sigma-modification leaks toward them (theta0 = nominal) instead of toward 0, as in Lab I.5.

Skipped (already measured in an earlier attempt): angle_none_long_step, angle_projection_long_step, angle_projection_sine.

![angle_sigma_nominal_steps](angle_sigma_nominal_steps.png)

![angle_sigma_nominal_sine](angle_sigma_nominal_sine.png)

| experiment | verdict | RMS e (norm) | RMS e last 25% | PE level | param drift (2nd half) | final params (ideal) | RMS angle error last 25% [rad] |
|---|---|---|---|---|---|---|---|
| angle_sigma_nominal_steps | OK | 0.0412 | 0.0274 | 0.00483 | 0.227 | k1=-0.354 (-0.398), k2=0.345 (0.805), d0=0.0624, l=0.348 (0.398) | 0.204 |
| angle_sigma_nominal_sine | OK | 0.0397 | 0.0262 | 0.0037 | 0.37 | k1=-0.243 (-0.398), k2=0.372 (0.805), d0=-0.0612, l=0.474 (0.398) | 0.302 |

**How to read the table.** *RMS e* is the normalised tracking error y - ym (0.01 = 1 % of omega_max). *PE level* = worst-case lambda_min/lambda_max of the windowed regressor covariance (≈0: not persistently exciting -> parameters need not converge to the ideal values; > ~0.01: PE holds -> parameters should approach the dashed ideal lines). *param drift* = largest parameter change during the second half of the run (large on a constant reference = parameter drift, the precursor of bursting/instability). Here e is the filtered error e^T P B0 (normalised).
