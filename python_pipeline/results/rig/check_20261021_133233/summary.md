# check - HARDWARE run 20261021_133233

![spin_pos](spin_pos.png)

![spin_neg](spin_neg.png)


## Checks

| check | measured | result |
|---|---|---|
| sample period | mean 10.00 ms, max 10.03 ms | PASS |
| velocity noise at rest | std 0.040 rad/s | info |
| potentiometer | 0.371 (0..1) | info - turn it and rerun to verify |
| u = +128 PWM | omega = +0.0 rad/s, d(theta) = +0.0 rad | FAIL - motor did not move (power supply? driver wiring? PIN_PWM?) |
| u = -128 PWM | omega = -0.4 rad/s, d(theta) = -0.8 rad | PASS |
