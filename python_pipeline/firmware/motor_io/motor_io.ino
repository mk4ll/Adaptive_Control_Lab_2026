/*
  motor_io.ino - thin real-time I/O layer for the coupled DC motor rig.

  The Arduino does NOT run any controller. All controllers live in Python
  (lab/controllers.py), so you flash this sketch ONCE and never touch it again.

  Every TS_US microseconds the Arduino:
    1. measures angle, velocity and the command potentiometer
    2. sends one line to the PC:   t_us,theta_rad,omega_rad_s,pot_0_1,u_pwm
    3. applies the latest PWM command it received from the PC (immediately on arrival)

  PC -> Arduino commands (one per line, '\n' terminated):
    B        begin streaming (resets the clock and the angle to zero)
    E        end streaming (motor off)
    <int>    PWM command in [-255, 255]

  Safety: while streaming, if no command arrives for WATCHDOG_MS the motor is switched off.

  ONLY EDIT THE CONFIGURATION SECTION BELOW to match your wiring.
*/

// ============================ CONFIGURATION ============================

// ---- Motor driver ----
// Values below match the lab bench (decoded from the original lab sketch, see firmware/backup/).
#define DRIVER_L298N    1       // EN (PWM) + IN1 + IN2   (L298N, L293D, ...)
#define DRIVER_PWM_DIR  2       // PWM + DIR              (Arduino Motor Shield, Cytron MD10C, ...)
#define DRIVER_TWO_PWM  3       // one PWM pin per direction (BTS7960 RPWM/LPWM, IN1/IN2 PWM)  <-- lab bench
#define DRIVER_TYPE     DRIVER_TWO_PWM

const int PIN_PWM    = 4;       // TWO_PWM: PWM for u > 0  | L298N: EN | PWM_DIR: PWM
const int PIN_IN1    = 5;       // TWO_PWM: PWM for u < 0  | L298N: IN1 | PWM_DIR: DIR
const int PIN_IN2    = 8;       // L298N IN2 only
const int MOTOR_SIGN = 1;       // set to -1 if a positive command makes the velocity negative
                                // (python run.py check tells you)

// ---- Velocity / angle sensor ----
#define SENSOR_ENCODER 1        // quadrature encoder -> angle and velocity
#define SENSOR_TACHO   2        // analog tachogenerator -> velocity (angle is integrated)
#define SENSOR_TYPE    SENSOR_ENCODER

const int   PIN_ENC_A          = 18;           // interrupt pins on the Mega: 2, 3, 18, 19, 20, 21
const int   PIN_ENC_B          = 19;
const int   ENC_DECODING       = 4;            // 1, 2 or 4 edges per encoder line (higher = finer but more interrupts)
const float ENC_COUNTS_PER_REV = 2150.0 * ENC_DECODING;   // 2150 rising edges of channel A per revolution
const int   ENC_SIGN           = 1;            // -1 to flip the measured direction

const int   PIN_TACHO           = A0;
const float TACHO_ZERO_ADC      = 512.0;       // ADC reading with the motor at rest  <-- CALIBRATE
const float TACHO_RAD_S_PER_ADC = 1.0;         // rad/s per ADC count               <-- CALIBRATE
const int   TACHO_SIGN          = 1;

const int   PIN_POT = A1;                      // optional command potentiometer (reference input)

const float OMEGA_FILTER_ALPHA = 0.5;          // velocity low-pass: 1.0 = off, smaller = smoother (adds lag)

// ---- Timing / communication ----
const unsigned long TS_US       = 10000;       // sample period: 10 ms = 100 Hz (must match lab/config.py TS)
const unsigned long WATCHDOG_MS = 200;
const long          BAUD        = 115200;      // must match lab/config.py BAUD

// ========================== END CONFIGURATION ==========================


// ---------------- encoder (quadrature decoding in interrupts, direction convention as the lab sketch) ----------------
volatile long    encCount = 0;
volatile uint8_t encPrev  = 0;
// index = (previous AB << 2) | current AB  ->  +1, -1 or 0 counts
const int8_t ENC_TABLE[16] = {0, -1, 1, 0,  1, 0, 0, -1,  -1, 0, 0, 1,  0, 1, -1, 0};

void encoderISR() {                       // x4: every edge of A and B
  uint8_t ab = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);
  encCount += ENC_TABLE[(encPrev << 2) | ab];
  encPrev = ab;
}

void encoderChangeA_ISR() {               // x2: every edge of A, direction from A == B
  encCount += (digitalRead(PIN_ENC_A) == digitalRead(PIN_ENC_B)) ? -1 : 1;
}

void encoderRisingISR() {                 // x1: rising edge of A, B gives the direction
  encCount += digitalRead(PIN_ENC_B) ? -1 : 1;
}

// ---------------- state ----------------
bool          streaming = false;
int           uCmd      = 0;
unsigned long t0        = 0;
unsigned long nextTick  = 0;
unsigned long lastCmdMs = 0;
long          prevCount = 0;
float         theta     = 0.0;
float         omega     = 0.0;
char          cmdBuf[16];
byte          cmdLen = 0;

// ---------------- motor ----------------
void applyPwm(int u) {
  int v = MOTOR_SIGN * constrain(u, -255, 255);
#if DRIVER_TYPE == DRIVER_TWO_PWM
  analogWrite(PIN_PWM, v > 0 ? v : 0);
  analogWrite(PIN_IN1, v < 0 ? -v : 0);
#elif DRIVER_TYPE == DRIVER_L298N
  digitalWrite(PIN_IN1, v > 0 ? HIGH : LOW);
  digitalWrite(PIN_IN2, v < 0 ? HIGH : LOW);
  analogWrite(PIN_PWM, abs(v));
#else
  digitalWrite(PIN_IN1, v >= 0 ? HIGH : LOW);
  analogWrite(PIN_PWM, abs(v));
#endif
}

// ---------------- measurement (called once per sample) ----------------
void measure() {
  const float ts = TS_US * 1e-6;
  float omegaRaw;
#if SENSOR_TYPE == SENSOR_ENCODER
  noInterrupts();
  long count = encCount;
  interrupts();
  float dTheta = ENC_SIGN * (count - prevCount) * TWO_PI / ENC_COUNTS_PER_REV;
  prevCount = count;
  theta += dTheta;
  omegaRaw = dTheta / ts;
#else
  omegaRaw = TACHO_SIGN * (analogRead(PIN_TACHO) - TACHO_ZERO_ADC) * TACHO_RAD_S_PER_ADC;
  theta += omegaRaw * ts;
#endif
  omega += OMEGA_FILTER_ALPHA * (omegaRaw - omega);
}

void resetState() {
  noInterrupts();
  encCount = 0;
  interrupts();
  prevCount = 0;
  theta = 0.0;
  omega = 0.0;
  uCmd = 0;
  applyPwm(0);
  t0 = micros();
  nextTick = t0;
  lastCmdMs = millis();
}

// ---------------- serial commands ----------------
void handleCommand(const char *cmd) {
  if (cmd[0] == 'B') {
    resetState();
    streaming = true;
  } else if (cmd[0] == 'E') {
    streaming = false;
    uCmd = 0;
    applyPwm(0);
  } else {
    uCmd = constrain(atoi(cmd), -255, 255);
    lastCmdMs = millis();
    if (streaming) applyPwm(uCmd);
  }
}

void readCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmdLen > 0) {
        cmdBuf[cmdLen] = '\0';
        handleCommand(cmdBuf);
        cmdLen = 0;
      }
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = c;
    }
  }
}

// ---------------- setup / loop ----------------
void setup() {
  pinMode(PIN_PWM, OUTPUT);
  pinMode(PIN_IN1, OUTPUT);
#if DRIVER_TYPE == DRIVER_L298N
  pinMode(PIN_IN2, OUTPUT);
#endif
  applyPwm(0);
#if SENSOR_TYPE == SENSOR_ENCODER
  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  encPrev = (digitalRead(PIN_ENC_A) << 1) | digitalRead(PIN_ENC_B);
  if (ENC_DECODING == 1) {
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encoderRisingISR, RISING);
  } else if (ENC_DECODING == 2) {
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encoderChangeA_ISR, CHANGE);
  } else {
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), encoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), encoderISR, CHANGE);
  }
#endif
  Serial.begin(BAUD);
  Serial.println("READY");
}

void loop() {
  readCommands();
  if (!streaming) return;

  unsigned long now = micros();
  if ((long)(now - nextTick) < 0) return;   // not time for the next sample yet
  nextTick += TS_US;

  measure();
  if (millis() - lastCmdMs > WATCHDOG_MS) {  // PC stopped talking -> motor off
    uCmd = 0;
    applyPwm(0);
  }

  Serial.print(now - t0);           Serial.print(',');
  Serial.print(theta, 4);           Serial.print(',');
  Serial.print(omega, 3);           Serial.print(',');
  Serial.print(analogRead(PIN_POT) / 1023.0, 3); Serial.print(',');
  Serial.println(uCmd);
}
