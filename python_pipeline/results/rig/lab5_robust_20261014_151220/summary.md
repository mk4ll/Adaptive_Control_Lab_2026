# lab5_robust - HARDWARE run 20261014_151220


## Design

Identified model: tau = 0.128 s (a = 7.84 1/s), K = 0.0198 rad/s/PWM, dead zone ~ 11 PWM, omega_max = 4.7 rad/s.

Normalised plant: dy/dt = -7.84 y + 8.35 u_n   (y = omega/4.7, u_n = u/255).

Reference model: dym/dt = -2.9 ym + 2.9 r  (time constant 0.345 s; open loop 0.128 s, dead time 0.115 s).

Robust settings: deadzone e0 = 0.02, sigma = 0.01, projection bound = 5.0, friction basis v0 = 0.1. Disturbance: 0.0 PWM.

Initial estimates = nominal values from the Lab I.1 model (ADI: 50 %, as in Lab I.4), with the Coulomb friction term seeded from the measured stop threshold; sigma and e-mod leak toward them (leaking toward 0, the textbook form, biases the feedforward gain l -> 0). Offset/friction terms adapt 0.3x slower. Friction basis driven by the reference-model velocity ym (non-zero at standstill, helps break stiction).


## MRAC with robust modifications

![mrac_none_steps](mrac_none_steps.png)

![mrac_none_sine](mrac_none_sine.png)

![mrac_none_long_step](mrac_none_long_step.png)

![mrac_deadzone_steps](mrac_deadzone_steps.png)

![mrac_deadzone_sine](mrac_deadzone_sine.png)

![mrac_deadzone_long_step](mrac_deadzone_long_step.png)

![mrac_sigma_steps](mrac_sigma_steps.png)

![mrac_sigma_sine](mrac_sigma_sine.png)

![mrac_sigma_long_step](mrac_sigma_long_step.png)

![mrac_emod_steps](mrac_emod_steps.png)

![mrac_emod_sine](mrac_emod_sine.png)

![mrac_emod_long_step](mrac_emod_long_step.png)

![mrac_projection_steps](mrac_projection_steps.png)

![mrac_projection_sine](mrac_projection_sine.png)

![mrac_projection_long_step](mrac_projection_long_step.png)

| experiment | verdict | RMS e (norm) | RMS e last 25% | PE level | param drift (2nd half) | final params (ideal) |
|---|---|---|---|---|---|---|
| mrac_none_steps | OK | 0.0767 | 0.0428 | 0.000998 | 0.133 | k=-0.101 (0.592), d0=0.0199, dc=0.263, l=0.512 (0.347) |
| mrac_none_sine | OK | 0.0847 | 0.046 | 0.00391 | 0.14 | k=-0.246 (0.592), d0=0.0339, dc=0.306, l=0.394 (0.347) |
| mrac_none_long_step | OK | 0.0231 | 0.0122 | -1.21e-14 | 0.0679 | k=0.0861 (0.592), d0=0.00152, dc=0.263, l=0.35 (0.347) |
| mrac_deadzone_steps | OK | 0.0814 | 0.0396 | 0.00098 | 0.121 | k=-0.147 (0.592), d0=0.0212, dc=0.29, l=0.516 (0.347) |
| mrac_deadzone_sine | OK | 0.0843 | 0.0474 | 0.00409 | 0.14 | k=-0.239 (0.592), d0=0.0364, dc=0.312, l=0.393 (0.347) |
| mrac_deadzone_long_step | OK | 0.0263 | 0.0163 | -1.2e-14 | 0.0806 | k=0.029 (0.592), d0=0.0133, dc=0.275, l=0.369 (0.347) |
| mrac_sigma_steps | poor tracking | 0.0851 | 0.053 | 0.00101 | 0.127 | k=0.171 (0.592), d0=0.0121, dc=0.19, l=0.381 (0.347) |
| mrac_sigma_sine | poor tracking | 0.0899 | 0.0615 | 0.00406 | 0.0986 | k=0.0868 (0.592), d0=0.0471, dc=0.262, l=0.255 (0.347) |
| mrac_sigma_long_step | OK | 0.0305 | 0.0243 | -1.2e-14 | 0.0607 | k=0.482 (0.592), d0=-0.0912, dc=0.173, l=0.293 (0.347) |
| mrac_emod_steps | OK | 0.0838 | 0.0389 | 0.000918 | 0.124 | k=-0.174 (0.592), d0=0.0163, dc=0.292, l=0.539 (0.347) |
| mrac_emod_sine | OK | 0.0832 | 0.0483 | 0.00419 | 0.148 | k=-0.223 (0.592), d0=0.0333, dc=0.303, l=0.354 (0.347) |
| mrac_emod_long_step | OK | 0.0242 | 0.012 | -1.21e-14 | 0.0511 | k=0.0956 (0.592), d0=0.00743, dc=0.269, l=0.36 (0.347) |
| mrac_projection_steps | OK | 0.0938 | 0.0364 | 0.000839 | 0.122 | k=-0.337 (0.592), d0=0.0212, dc=0.33, l=0.615 (0.347) |
| mrac_projection_sine | OK | 0.0926 | 0.0483 | 0.00403 | 0.142 | k=-0.354 (0.592), d0=0.028, dc=0.311, l=0.488 (0.347) |
| mrac_projection_long_step | OK | 0.0252 | 0.0122 | -1.21e-14 | 0.0714 | k=0.0192 (0.592), d0=0.0171, dc=0.278, l=0.376 (0.347) |

![mrac_long_comparison](mrac_long_comparison.png)


## ADI with robust modifications

![adi_none_steps](adi_none_steps.png)

![adi_none_sine](adi_none_sine.png)

![adi_none_long_step](adi_none_long_step.png)

![adi_deadzone_steps](adi_deadzone_steps.png)

![adi_deadzone_sine](adi_deadzone_sine.png)

![adi_deadzone_long_step](adi_deadzone_long_step.png)

![adi_sigma_steps](adi_sigma_steps.png)

![adi_sigma_sine](adi_sigma_sine.png)

![adi_sigma_long_step](adi_sigma_long_step.png)

![adi_emod_steps](adi_emod_steps.png)

![adi_emod_sine](adi_emod_sine.png)

![adi_emod_long_step](adi_emod_long_step.png)

![adi_projection_steps](adi_projection_steps.png)

![adi_projection_sine](adi_projection_sine.png)

![adi_projection_long_step](adi_projection_long_step.png)

| experiment | verdict | RMS e (norm) | RMS e last 25% | PE level | param drift (2nd half) | final params (ideal) |
|---|---|---|---|---|---|---|
| adi_none_steps | OK | 0.115 | 0.038 | 0.000521 | 0.133 | a_hat=-2.1 (-7.84), d0_hat=-0.147, dc_hat=-1.11, b_hat=4.63 (8.35) |
| adi_none_sine | poor tracking | 0.105 | 0.0633 | 0.00146 | 0.416 | a_hat=-2.24 (-7.84), d0_hat=-0.151, dc_hat=-1.19, b_hat=4.94 (8.35) |
| adi_none_long_step | OK | 0.0337 | 0.0257 | -1.1e-14 | 0.269 | a_hat=-2.74 (-7.84), d0_hat=0.0818, dc_hat=-1.02, b_hat=4.66 (8.35) |
| adi_deadzone_steps | OK | 0.124 | 0.0442 | 0.000476 | 0.144 | a_hat=-1.94 (-7.84), d0_hat=-0.14, dc_hat=-1.15, b_hat=4.56 (8.35) |
| adi_deadzone_sine | poor tracking | 0.101 | 0.0694 | 0.00141 | 0.378 | a_hat=-2.38 (-7.84), d0_hat=-0.134, dc_hat=-1.09, b_hat=4.94 (8.35) |
| adi_deadzone_long_step | OK | 0.0337 | 0.0246 | -1.11e-14 | 0.221 | a_hat=-2.76 (-7.84), d0_hat=0.101, dc_hat=-1, b_hat=4.68 (8.35) |
| adi_sigma_steps | OK | 0.12 | 0.0438 | 0.000456 | 0.332 | a_hat=-2.83 (-7.84), d0_hat=-0.202, dc_hat=-0.77, b_hat=4.69 (8.35) |
| adi_sigma_sine | poor tracking | 0.116 | 0.0899 | 0.00192 | 0.306 | a_hat=-2.74 (-7.84), d0_hat=-0.157, dc_hat=-1.01, b_hat=4.77 (8.35) |
| adi_sigma_long_step | OK | 0.0434 | 0.0396 | -1.1e-14 | 0.0838 | a_hat=-3.61 (-7.84), d0_hat=0.343, dc_hat=-0.76, b_hat=4.38 (8.35) |
| adi_emod_steps | OK | 0.123 | 0.047 | 0.00051 | 0.163 | a_hat=-1.99 (-7.84), d0_hat=-0.129, dc_hat=-1.13, b_hat=4.57 (8.35) |
| adi_emod_sine | poor tracking | 0.104 | 0.0725 | 0.00152 | 0.389 | a_hat=-2.35 (-7.84), d0_hat=-0.142, dc_hat=-1.09, b_hat=4.92 (8.35) |
| adi_emod_long_step | OK | 0.0346 | 0.0256 | -1.1e-14 | 0.196 | a_hat=-2.8 (-7.84), d0_hat=0.124, dc_hat=-0.977, b_hat=4.65 (8.35) |
| adi_projection_steps | OK | 0.116 | 0.0421 | 0.000501 | 0.167 | a_hat=-2.21 (-7.84), d0_hat=-0.161, dc_hat=-1.01, b_hat=4.59 (8.35) |
| adi_projection_sine | poor tracking | 0.107 | 0.069 | 0.0017 | 0.474 | a_hat=-2.12 (-7.84), d0_hat=-0.156, dc_hat=-1.19, b_hat=4.92 (8.35) |
| adi_projection_long_step | OK | 0.033 | 0.0233 | -1.09e-14 | 0.226 | a_hat=-2.76 (-7.84), d0_hat=0.0884, dc_hat=-1.01, b_hat=4.66 (8.35) |

![adi_long_comparison](adi_long_comparison.png)

**How to read the table.** *RMS e* is the normalised tracking error y - ym (0.01 = 1 % of omega_max). *PE level* = worst-case lambda_min/lambda_max of the windowed regressor covariance (≈0: not persistently exciting -> parameters need not converge to the ideal values; > ~0.01: PE holds -> parameters should approach the dashed ideal lines). *param drift* = largest parameter change during the second half of the run (large on a constant reference = parameter drift, the precursor of bursting/instability).


**What to look for:** with *none*, ||theta|| may keep growing on the long step (drift: no PE + noise/disturbance). *sigma* and *e-mod* bound the parameters at the cost of a small steady bias, *deadzone* freezes adaptation once |e| < e0, *projection* keeps them in the box without biasing them inside it.
