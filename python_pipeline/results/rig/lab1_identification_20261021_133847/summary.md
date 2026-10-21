# lab1_identification - HARDWARE run 20261021_133847


## A. Step tests: steady-state gain and time constant

![hysteresis](hysteresis.png)

| u [PWM] | omega_ss [rad/s] | model omega_ss | dead time Td [s] | tau (63%) - Td [s] | rise 10-90% [s] | settled? |
|---|---|---|---|---|---|---|
| 30 | 0 | 0.435 | 0 | 0 | 0 | yes |
| 50 | 0 | 0.816 | 4e-06 | 0 | 0 | yes |
| 75 | 0 | 1.29 | 0 | 0 | 0 | yes |
| 100 | 1.59 | 1.77 | 0.13 | 0.21 | 0.36 | yes |
| 130 | 2.43 | 2.34 | 0.08 | 0.14 | 0.32 | yes |
| 160 | 3.09 | 2.92 | 0.09 | 0.13 | 0.3 | yes |
| 200 | 3.71 | 3.68 | 0.09 | 0.1 | 0.23 | yes |
| 255 | 4.59 | 4.73 | 0.09 | 0.09 | 0.18 | yes |
| -30 | 0 | -0.535 | 0 | 0 | 0 | yes |
| -50 | 0 | -0.891 | 0 | 0 | 0 | yes |
| -75 | -1.19 | -1.34 | 0.13 | 0.32 | 0.7 | yes |
| -100 | -2.07 | -1.78 | 0.09 | 0.15 | 0.4 | yes |
| -130 | -2.92 | -2.32 | 0.09 | 0.14 | 0.35 | yes |
| -160 | -3.49 | -2.85 | 0.09 | 0.13 | 0.32 | yes |
| -200 | -4.06 | -3.56 | 0.09 | 0.09 | 0.25 | yes |
| -255 | -4.74 | -4.55 | 0.08 | 0.1 | 0.21 | yes |

Identified parameters. Kinetic line omega = K(u - u0) from all moving samples of the slow triangle; tau and Td = medians over the moving steps (rise_10_90 ~ 2.2*tau is a consistency check). ub > us means stick-slip hysteresis: the shaft needs more PWM to start than to keep moving. Breakaway varies from one start to the next (shaft position, gearbox), compare the two ub rows.

|  | u > 0 | u < 0 | average (used for design) |
|---|---|---|---|
| gain K, slow triangle (used) [rad/s/PWM] | 0.0191 | 0.0178 | 0.0185 |
| gain K, steps (cross-check) | 0.0188 | 0.0192 |  |
| dead zone u0 of the kinetic line [PWM] | 7.2 | 0 |  |
| breakaway from rest ub (steps) [PWM] | 87.5 | 62.5 |  |
| breakaway from rest (slow triangle) [PWM] | 113 | 199 |  |
| stop threshold us (slow triangle) [PWM] | 68.1 | 55.3 |  |
| time constant tau [s] | 0.13 | 0.135 | 0.133 |
| pole a = 1/tau [1/s] | 7.69 | 7.41 | 7.55 |
| dead time Td [s] |  |  | 0.09 |
| b = a*K |  |  | 0.139 |
| omega_max [rad/s] |  |  | 4.55 |

![static_characteristic](static_characteristic.png)

![step_responses](step_responses.png)

Model saved to `/home/stathisliap/HMTY/Adaptive_Control/results/rig/model.json`


## B. Model validation

Model = first order + dead time + stick-slip. fit % = 100 * (1 - ||omega - omega_model|| / ||omega - mean(omega)||); above ~80 % is good.

![val_step](val_step.png)

![val_sine](val_sine.png)

![val_ramp](val_ramp.png)

| input | fit % | fit % while both moving | RMS error [rad/s] |
|---|---|---|---|
| val_step | 60.8 | n/a | 0.453 |
| val_sine | 82.1 | 85.1 | 0.443 |
| val_ramp | -2.489e+05 | n/a | 2.11 |

*fit while moving* judges the dynamic model (gain, tau, Td) without the random breakaway instants.


## C. P and PI velocity control designed from the model

Plant: K = 0.01845 rad/s/PWM, tau = 0.133 s, dead time Td = 0.09 s. Lambda tuning: lambda = max(tau/speedup, 2*Td).

- P:  Kp = tau/(K(lambda+Td)) = **26.6** (lambda = 0.18 s), predicted steady-state ratio omega/r = K Kp/(1 + K Kp) = 0.329
- PI: Kp = tau/(K(lambda+Td)) = **26.6**, Ki = Kp/tau = **200.7** (lambda = 0.18 s), zero steady-state error

Small references sit inside the stick-slip band, so expect stick-slip cycling there: the controller must build up ~ub PWM to break away, then the shaft overshoots and sticks again.

![P_control](P_control.png)

![PI_control](PI_control.png)

| controller | measured omega/r at steady state | RMS error [rad/s] |
|---|---|---|
| P_control | 0 | 1.93 |
| PI_control | nan | 1.36 |

(Predicted ratio: P = 0.329, PI = 1.000. If the P output K_p*e stays below the breakaway PWM ub, the shaft never starts (ratio 0): P control alone cannot overcome stick-slip, the PI integrator builds up the missing PWM, which shows as a short stall at every sign change.)
