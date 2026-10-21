# extras_lab5dz - HARDWARE run 20261021_143533

Identified model: tau = 0.133 s (a = 7.55 1/s), K = 0.0185 rad/s/PWM, dead zone ~ 4 PWM, omega_max = 4.5 rad/s.

Normalised plant: dy/dt = -7.55 y + 7.81 u_n   (y = omega/4.5, u_n = u/255).

Reference model: dym/dt = -3.7 ym + 3.7 r  (time constant 0.27 s; open loop 0.133 s, dead time 0.09 s).


## Lab I.5 deadzone modification with e0 = 0.06 (was 0.02)

In Lab I.5 the deadzone e0 = 0.02 was below the velocity noise (|e| ~ 0.03-0.05), so adaptation never switched off and the ADI parameters kept drifting. Here e0 = 0.06; everything else as in Lab I.5.

| experiment | verdict | RMS e (norm) | RMS e last 25% | PE level | param drift (2nd half) | final params (ideal) |
|---|---|---|---|---|---|---|

**How to read the table.** *RMS e* is the normalised tracking error y - ym (0.01 = 1 % of omega_max). *PE level* = worst-case lambda_min/lambda_max of the windowed regressor covariance (≈0: not persistently exciting -> parameters need not converge to the ideal values; > ~0.01: PE holds -> parameters should approach the dashed ideal lines). *param drift* = largest parameter change during the second half of the run (large on a constant reference = parameter drift, the precursor of bursting/instability).
