// =====================================================
//  motor_io.ino — Generic I/O firmware for the coupled DC motors
//  (Arduino Mega 2560 + YL-86 / L9110 driver, same wiring as Robust Lab)
//  -----------------------------------------------------
//  Used for: circuit check (circuit_check.m) and Lab I.1 identification.
//
//  YL-86 (Convention B):
//    IA=LOW, IB=PWM -> forward  (+)
//    IA=PWM, IB=LOW -> reverse  (-)
//    IA=LOW, IB=LOW -> coast
//
//  Serial @115200, commands (newline terminated):
//    P<int>   signed PWM in [-255, 255]   e.g. "P200", "P-150"
//    S        stop (coast)
//    Z        zero encoder count
//
//  Streams every Ts_ms:  D,<t_ms>,<pwm>,<count>,<rpm>
// =====================================================

const int motorIN_A = 5;   // IA on YL-86
const int motorIN_B = 4;   // IB on YL-86
const int encA      = 18;  // Encoder channel A (interrupt)
const int encB      = 19;  // Encoder channel B (direction)

const float PPR = 2150.0;          // counts per output-shaft revolution (1x decoding)
const unsigned long Ts_ms = 20;    // sampling period

volatile long encoderPos = 0;
long previousPos = 0;
unsigned long previousTime = 0;
int pwmCmd = 0;

void setMotor(int pwm) {
  pwm = constrain(pwm, -255, 255);
  pwmCmd = pwm;
  if (pwm >= 0) {            // forward
    analogWrite(motorIN_A, 0);
    analogWrite(motorIN_B, pwm);
  } else {                   // reverse
    analogWrite(motorIN_B, 0);
    analogWrite(motorIN_A, -pwm);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(motorIN_A, OUTPUT);
  pinMode(motorIN_B, OUTPUT);
  pinMode(encA, INPUT_PULLUP);
  pinMode(encB, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(encA), readEncoder, RISING);
  setMotor(0);
  Serial.println("READY");
  previousTime = millis();
}

void loop() {
  // --- 1. Commands ---
  if (Serial.available() > 0) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();
    if (msg.startsWith("P")) {
      setMotor(msg.substring(1).toInt());
    } else if (msg.startsWith("S")) {
      setMotor(0);
    } else if (msg.startsWith("Z")) {
      noInterrupts();
      encoderPos = 0;
      interrupts();
      previousPos = 0;
    }
  }

  // --- 2. Sampling ---
  unsigned long currentMillis = millis();
  if (currentMillis - previousTime >= Ts_ms) {
    unsigned long dt = currentMillis - previousTime;

    noInterrupts();
    long currentPos = encoderPos;
    interrupts();

    float rpm = ((float)(currentPos - previousPos) / PPR) * (60000.0 / (float)dt);

    Serial.print("D,");
    Serial.print(currentMillis); Serial.print(",");
    Serial.print(pwmCmd);        Serial.print(",");
    Serial.print(currentPos);    Serial.print(",");
    Serial.println(rpm, 3);

    previousTime = currentMillis;
    previousPos  = currentPos;
  }
}

void readEncoder() {
  if (digitalRead(encB) == HIGH) encoderPos++;
  else encoderPos--;
}
