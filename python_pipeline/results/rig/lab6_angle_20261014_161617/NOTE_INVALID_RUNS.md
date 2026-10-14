# Hardware fault during this run (2026-10-14 ~16:21)

At t = 18.9 s of `angle_deadzone_sine` the encoder reading froze (theta = -2.511 rad, omega = 0)
while the controller commanded +255 PWM. Either the motor stopped (power / driver / motor wire)
or the encoder signal was lost. Everything after that instant is INVALID:

- angle_deadzone_sine (after t = 18.9 s), angle_sigma_*, angle_emod_*, angle_projection_*,
  angle_none_long_step, angle_projection_long_step

Valid: angle_none_steps, angle_none_sine, angle_deadzone_steps (and the first 18.9 s of angle_deadzone_sine).
A stall / sensor-loss watchdog (STALL_TIME in lab/config.py) was added afterwards; re-run Lab I.6 after
checking the hardware.
