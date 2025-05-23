/*
@original-company: Hiwonder
@original-date:    2024-03-01
@version:  2.0_shy
@description: program of hardware component of SomaSoMouse
*/

#include <SoftwareSerial.h> //software serial library
#include "MPU6050.h" //MPU6050 library
#include "Wire.h" //I2C library

// RX and TX pins of the Bluetooth
#define BTH_RX 11
#define BTH_TX 12


// create the minimum and maximum store values of the potentiometers
float min_list[5] = {0, 0, 0, 0, 0};
float max_list[5] = {255, 255, 255, 255, 255};
// data variables read by each finger
float sampling[5] = {0, 0, 0, 0, 0}; 

// potentiometer calibration flag
bool turn_on = true;

// initialize Bluetooth communication serial port
SoftwareSerial Bth(BTH_RX, BTH_TX);

// fingers part 1, handles thumb, pointer, middle, and ring fingers
// 2 (header) + 4 (thumb) + 4 (pointer) + 4 (middle) + 4 (ring) + 2 (footer for byte alignment)
struct finger_d {
  uint8_t header[2] = {0xF1, 0xF1};
  float thumb = 0.0f;
  float pointer = 0.0f;
  float middle = 0.0f;
  float ring = 0.0f;
  uint8_t footer[2] = {0xFF, 0xFF};
};

finger_d fingers;

// fingers part 2 and accelerometer data, handles pinky and acceleration data
// 2 (header) + 4 (pinky) + 4 (ax) + 4 (ay) + 4 (az) + 2 (byte alignment footer)
struct pinky_accel_d {
  uint8_t header[2] = {0xF2, 0xF2};
  float pinky = 0.0f;
  float ax1, ay1, az1;
  uint8_t footer[2] = {0xFF, 0xFF};
};

pinky_accel_d pinky_accel;

// gyroscope measured angular velocity struct, also x inclination
// 2 (header) + 4 (gx1) + 4 (gy1) + 4 (gz1) + 4 (radianX_last) + 2 (byte alignment footer)
struct rotation_d {
  uint8_t header[2] = {0xF3, 0xF3};
  float gx1, gy1, gz1;
  float radianX_last; // the final obtained X-axis inclination angle
  uint8_t footer[2] = {0xFF, 0xFF};
};

rotation_d rot_data;

// extra data that I wanted to share that didn't really fit anywhere else, right now just the y inclination
// 2 (header) + 4 (radianY_last) + 14 (filler, byte alignment footer)
struct extra_d {
  uint8_t header[2] = {0xF4, 0xF4};
  float radianY_last; // the final obtained Y-axis inclination angle
  uint8_t footer[14] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
};

extra_d misc_data;

// float parameter mapping function
float float_map(float in, float left_in, float right_in, float left_out, float right_out)
{
  return (in - left_in) * (right_out - left_out) / (right_in - left_in) + left_out;
}

float map_and_clamp(float in, float left_in, float right_in, float left_out, float right_out)
{
  float out = float_map(in, left_in, right_in, left_out, right_out);
  out = out > left_out ? left_out : out;  // limit the maximum value to left_out
  out = out < right_out ? right_out : out;   // limit the minimum value to right_out
  return out;
}

#define R_OUT 100
#define L_OUT 200

// MPU6050 related variables
MPU6050 accelgyro;
int16_t ax, ay, az;
int16_t gx, gy, gz;
float ax0, ay0, az0;
float gx0, gy0, gz0;

// accelerometer calibration variable
int ax_offset, ay_offset, az_offset, gx_offset, gy_offset, gz_offset;


bool finger_ready = false;
bool position_ready = false;

void set_leds(bool first, bool second, bool third, bool fourth, bool fifth) {
  digitalWrite(2, first ? LOW : HIGH);
  digitalWrite(3, second ? LOW : HIGH);
  digitalWrite(4, third ? LOW : HIGH);
  digitalWrite(5, fourth ? LOW : HIGH);
  digitalWrite(6, fifth ? LOW : HIGH);
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  // initialize function button)
  pinMode(7, INPUT_PULLUP);
  // configure each finger's potentiometer
  pinMode(A0, INPUT);
  pinMode(A1, INPUT);
  pinMode(A2, INPUT);
  pinMode(A3, INPUT);
  pinMode(A6, INPUT);
  // configure LEDs
  pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);

  // configure Bluetooth
  Bth.begin(9600);
  delay(250);
  Bth.print("AT+ROLE=S");  // set Bluetooth to slave mode
  delay(275);
  
  Bth.print("AT+NAME=handbot");  // set Bluetooth name
  delay(150);
  Bth.print("AT+PIN=0000");  // set Bluetooth PIN
  delay(150);
  Bth.print("AT+RESET");  // perform a soft reset of the Bluetooth module
  delay(250);
  Bth.print("AT+MODE=0"); // Begin pairing mode
  delay(200);

  // configure MPU6050
  Wire.begin();
  Wire.setClock(20000);
  accelgyro.initialize();
  accelgyro.setFullScaleGyroRange(3); // set the range of angular velocity
  accelgyro.setFullScaleAccelRange(1); // set the range of acceleration
  delay(200);
  reset_offsets();
}

void reset_offsets() {
  
  accelgyro.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);  // obtain current data of each axis for calibration
  ax_offset = ax;  // calibration data for the X-axis acceleration
  ay_offset = ay;  // calibration data for the Y-axis acceleration
  az_offset = az - 8192;  // calibration data for the Z-axis acceleration
  gx_offset = gx; // calibration data for the X-axis angular velocity
  gy_offset = gy; // calibration data for the Y-axis angular velocity
  gz_offset = gz; // calibration data for the Z-axis angular velocity
}

#define INIT_PHASE 0
#define AWAKE_PHASE 1
#define LED_CHECK_PHASE 2
#define MAX_STRETCH_GET_PHASE 3
#define PAUSE_PHASE 4
#define STRETCH_ESCAPE_PHASE 5
#define ESCAPE_NOTED_PHASE 6
#define MIN_STRETCH_PREPARE_PHASE 7
#define MIN_STRETCH_GET_PHASE 8

uint8_t init_step = 0;
// read potentiometer data of each finger
void finger() {
  static uint32_t timer_sampling;
  static uint32_t timer_init;

  if (timer_sampling <= millis() && !finger_ready)
  {
    sampling[0] += analogRead(14);
    sampling[0] /= 2.0;
    fingers.thumb = map_and_clamp( sampling[0],min_list[0], max_list[0], L_OUT, R_OUT);
    sampling[1] += analogRead(15);
    sampling[1] /= 2.0;
    fingers.pointer = map_and_clamp( sampling[1],min_list[1], max_list[1], L_OUT, R_OUT);
    sampling[2] += analogRead(16);
    sampling[2] /= 2.0;
    fingers.middle = map_and_clamp( sampling[2],min_list[2], max_list[2], L_OUT, R_OUT);
    sampling[3] += analogRead(17);
    sampling[3] /= 2.0;
    fingers.ring = map_and_clamp( sampling[3],min_list[3], max_list[3], L_OUT, R_OUT);
    sampling[4] += analogRead(A6); // Read data of little finger. I2C uses A4 and A5 ports, therefore, it cannot read continuously starting from A0
    sampling[4] /= 2.0;
    pinky_accel.pinky = map_and_clamp( sampling[4],min_list[4], max_list[4], L_OUT, R_OUT);

    // After calibration, it is safe to start sending data
    if (!turn_on) {
      finger_ready = true;
      //Serial.println("FINGER READY TO SEND");
    }
    // Otherwise, send calibration message
    else {
      Bth.write("-----CALIBRATING----");
    }

    timer_sampling = millis() + 20;

  }

  if (turn_on && timer_init < millis())
  {
    switch (init_step)
    {
      case INIT_PHASE:
        set_leds(true, false, true, false, true);
        timer_init = millis() + 20;
        init_step++;
        break;
      case AWAKE_PHASE:
        set_leds(true, true, true, true, true);
        timer_init = millis() + 200;
        init_step++;
        break;
      case LED_CHECK_PHASE:
        set_leds(true, false, false, false, true);
        timer_init = millis() + 50;
        init_step++;
        break;
      case MAX_STRETCH_GET_PHASE:
        set_leds(true, true, false, false, false);
        timer_init = millis() + 500;
        init_step++;
        //Serial.print("max_list:");
        for (int i = 14; i <= 18; i++)
        {
          max_list[i - 14] = sampling[i - 14];
          //Serial.print(max_list[i - 14]);
          //Serial.print("-");
        }
        //Serial.println();
        break;
      case PAUSE_PHASE:
        init_step++;
        break;
      case STRETCH_ESCAPE_PHASE:
        if ((max_list[1] - sampling[1]) > 50)
        {
          init_step++;
          set_leds(false, false, false, false, false);
          timer_init = millis() + 2000;
        }
        break;
      case ESCAPE_NOTED_PHASE:
        set_leds(true, true, true, false, false);
        timer_init = millis() + 200;
        init_step++;
        break;
      case MIN_STRETCH_PREPARE_PHASE:
        set_leds(true, true, true, true, true);
        timer_init = millis() + 50;
        init_step++;
        break;
      case MIN_STRETCH_GET_PHASE:
        set_leds(true, false, true, false, true);
        timer_init = millis() + 500;
        init_step++;
        //Serial.print("min_list:");
        for (int i = 14; i <= 18; i++)
        {
          min_list[i - 14] = sampling[i - 14];
        //  Serial.print(min_list[i - 14]);
        //  Serial.print("-");
        }
        //Serial.println();
        turn_on = false;
        set_leds(false, false, false, false, false);
        break;

      default:
        break;
    }
  }
}


float radianX;
float radianY;
float radianZ;

// update data of inclination sensor
void update_mpu6050()
{
  static uint32_t timer_u;
  if (timer_u < millis() && !position_ready)
  {
    // put your main code here, to run repeatedly:
    timer_u = millis() + 50;
    accelgyro.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

    ax0 = ((float)(ax)) * 0.3 + ax0 * 0.7;  // filter the read value
    ay0 = ((float)(ay)) * 0.3 + ay0 * 0.7;
    az0 = ((float)(az)) * 0.3 + az0 * 0.7;
    pinky_accel.ax1 = (ax0 - ax_offset) /  8192.0;  // calibrate and convert to the multiples of the gravity acceleration
    pinky_accel.ay1 = (ay0 - ay_offset) /  8192.0;
    pinky_accel.az1 = (az0 - az_offset) /  8192.0;

    gx0 = ((float)(gx)) * 0.3 + gx0 * 0.7;  // filter the read value of angular velocity
    gy0 = ((float)(gy)) * 0.3 + gy0 * 0.7;
    gz0 = ((float)(gz)) * 0.3 + gz0 * 0.7;
    rot_data.gx1 = (gx0 - gx_offset);  // calibrate angular velocity
    rot_data.gy1 = (gy0 - gy_offset);
    rot_data.gz1 = (gz0 - gz_offset);


    // complementary calculation for x-axis inclination angle
    radianX = atan2(pinky_accel.ay1, pinky_accel.az1);
    radianX = radianX * 180.0 / 3.1415926;
    float radian_temp = (float)(rot_data.gx1) / 16.4 * 0.02;
    rot_data.radianX_last = 0.8 * (rot_data.radianX_last + radian_temp) + (-radianX) * 0.2;

    // complementary calculation for y-axis inclination angle
    radianY = atan2(pinky_accel.ax1, pinky_accel.az1);
    radianY = radianY * 180.0 / 3.1415926;
    radian_temp = (float)(rot_data.gy1) / 16.4 * 0.01;
    misc_data.radianY_last = 0.8 * (misc_data.radianY_last + radian_temp) + (-radianY) * 0.2;

    if (!turn_on) {
      position_ready = true;
      //Serial.println("POSITION READY TO SEND");
    }
    // Otherwise, send calibration message
    //else {
    //  Bth.write("-----CALIBRATING----");
    //}
  }
}

bool key_state = false;
uint32_t hold_time = 0;

void actions() {
  if (key_state) {
    ++hold_time;
    set_leds(hold_time > 4, hold_time > 8, hold_time > 12, hold_time > 16, hold_time > 20);
  }
  // if K3 button is pressed 
  if(key_state && digitalRead(7) == true)
  {
    //Serial.println("BUTTON RELEASED");
    key_state = false;
    //Serial.println((unsigned long) hold_time);
    if (hold_time >= 8 && hold_time < 20) { //reset pointing direction
      reset_offsets();
    }
    else if (hold_time >= 20) { //reset finger calibration
      init_step = 0;
      turn_on = true;
    }
    hold_time = 0;
    set_leds(false, false, false, false, false);
  }
  if (digitalRead(7) == false && key_state == false)
  {
    //Serial.println("K3 held!");
    key_state = true;
  }
}

void loop() {
  // prepare data to be sent in functions
  finger();  // update data of finger potentiometers
  update_mpu6050();  // update data of inclination sensor
  if (finger_ready && position_ready) {
    //Serial.println("SENDING DATA");
    Bth.write((uint8_t *) &fingers, sizeof(finger_d));
    delay(5);
    Bth.write((uint8_t *) &pinky_accel, sizeof(pinky_accel_d));
    delay(5);
    Bth.write((uint8_t *) &rot_data, sizeof(rotation_d));
    delay(5);
    Bth.write((uint8_t *) &misc_data, sizeof(extra_d));
    delay(5);
    finger_ready = false;
    position_ready = false;
    //Serial.println("DATA SENT");
  }
  actions(); // do other things
}
