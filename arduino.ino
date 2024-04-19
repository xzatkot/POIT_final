#include <Servo.h>

const int trigPin = 7;
const int echoPin = 6;
const int servoPin = 5;

Servo servo;

void setup() {
  Serial.begin(9600);
  
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  servo.attach(servoPin);
}

void loop() {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  long duration = pulseIn(echoPin, HIGH);
  
  float distance_cm = duration * 0.0343 / 2.0;

  if (distance_cm < 20) {
    servo.write(0);
  }
  else {
    servo.write(90);
  }
  
  Serial.println(distance_cm);
  
  delay(1000);
}