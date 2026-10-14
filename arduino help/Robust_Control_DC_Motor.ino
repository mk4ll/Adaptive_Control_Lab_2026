#include <ros.h>
#include <std_msgs/Float32.h>
#include <std_msgs/Int16.h>

ros::NodeHandle nh;

// Pins
#define ENCA 2
#define ENCB 3
#define IN1 4 
#define IN2 5 
#define IN3 6 
#define IN4 7 

// globals
long prevT = 0;
int posPrev = 0;
// Use the "volatile" directive for variables
// used in an interrupt
volatile int pos_i = 0;
volatile float velocity_i = 0;
volatile long prevT_i = 0;


std_msgs::Float32 ang_vel; 

ros::Publisher angular_velValue("Angular_Velocity", &ang_vel);


float v1Filt = 0;
float v1Prev = 0;
float v2Filt = 0;
float v2Prev = 0;

void pwm_input(const std_msgs::Int16& pwm_value){
   
  if ( pwm_value.data > 0 )
  {
  setMotor(false, pwm_value.data,IN1,IN2);
  }
  else 
  {
  setMotor(true, abs(pwm_value.data),IN1,IN2);
  }

 
}

void pwm_input_d(const std_msgs::Int16& pwm_value_d){
   
  if ( pwm_value_d.data > 0 )
  {

  setMotor(false, pwm_value_d.data,IN3,IN4);
  }
  else 
  {

  setMotor(true, abs(pwm_value_d.data),IN3,IN4);
  }

 
}


ros::Subscriber<std_msgs::Int16> pwm("PWM_Control_Input", &pwm_input);
ros::Subscriber<std_msgs::Int16> disturbance("PWM_Disturbance", &pwm_input_d);

void setup() {
  
  pinMode(ENCA,INPUT_PULLUP);
  pinMode(ENCB,INPUT_PULLUP);
  pinMode(IN1,OUTPUT);
  pinMode(IN2,OUTPUT);
  pinMode(IN3,OUTPUT);
  pinMode(IN4,OUTPUT); 
  attachInterrupt(digitalPinToInterrupt(ENCA),readEncoder,RISING);
  
  // ROS Setup
  nh.getHardware()->setBaud(57600);
  nh.initNode();
  nh.advertise(angular_velValue);
  nh.subscribe(pwm);
  nh.subscribe(disturbance);
}

void loop() {
 
  // read the position and velocity
  int pos = 0;
  float velocity2 = 0;
  noInterrupts(); // disable interrupts temporarily while reading
  pos = pos_i;
  velocity2 = velocity_i;
  interrupts(); // turn interrupts back on

  // Compute velocity with method 1
  long currT = micros();
  float deltaT = ((float) (currT-prevT))/1.0e6;
  float velocity1 = (pos - posPrev)/deltaT;
  posPrev = pos;
  prevT = currT;

  // Convert count/s to RPM
  float v1 = velocity1/2086.0*60.0;
  float v2 = velocity2/2086.0*60.0;

  // Low-pass 1st-Order Butterworth filter (25 Hz cutoff)
  v1Filt = 0.854*v1Filt + 0.0728*v1 + 0.0728*v1Prev;
  v1Prev = v1;
  v2Filt = 0.854*v2Filt + 0.0728*v2 + 0.0728*v2Prev;
  v2Prev = v2;

  ang_vel.data=v1Filt;

  float current_angle = pos/2086.0*360.0;
  

  angular_velValue.publish(&ang_vel);
  nh.spinOnce();
  delay(100);
  
}

void setMotor(boolean dir, int pwmVal, int in1, int in2){
   // Motor speed
  
  if(dir == true){ 
    // CCW -
    digitalWrite(in2,HIGH);
    analogWrite(in1,255-pwmVal);
  }
  else if(dir == false){
    // CW +
    analogWrite(in1,pwmVal);
    digitalWrite(in2,LOW);
    
  }
}

void readEncoder(){
  // Read encoder B when ENCA rises
  int b = digitalRead(ENCB);
  int increment = 0;
  if(b>0){
    // If B is high, increment forward
    increment = 1;
  }
  else{
    // Otherwise, increment backward
    increment = -1;
  }
  pos_i = pos_i + increment;

  // Compute velocity with method 2
  long currT = micros();
  float deltaT = ((float) (currT - prevT_i))/1.0e6;
  velocity_i = increment/deltaT;
  prevT_i = currT;
}
