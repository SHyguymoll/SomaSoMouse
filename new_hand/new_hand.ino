/*
@company: Hiwonder
@date:    2024-03-01
@version:  2.0
@description: wireless glove control program
*/

#include <SoftwareSerial.h> //software serial library
#include "LobotServoController.h" //robot control signal library
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
// finger-related servo variables
float data[5] = {1500, 1500, 1500, 1500, 1500};
uint16_t ServePwm[5] = {1500, 1500, 1500, 1500, 1500};
uint16_t ServoPwmSet[5] = {1500, 1500, 1500, 1500, 1500};
// potentiometer calibration flag
bool turn_on = true;

// initialize Bluetooth communication serial port
SoftwareSerial Bth(BTH_RX, BTH_TX);
// the control object of the robot
// LobotServoController lsc(Bth);

// float parameter mapping function
float float_map(float in, float left_in, float right_in, float left_out, float right_out)
{
  return (in - left_in) * (right_out - left_out) / (right_in - left_in) + left_out;
}

// MPU6050 related variables
MPU6050 accelgyro;
int16_t ax, ay, az;
int16_t gx, gy, gz;
float ax0, ay0, az0;
float gx0, gy0, gz0;
float ax1, ay1, az1;
float gx1, gy1, gz1;

// accelerometer calibration variable
int ax_offset, ay_offset, az_offset, gx_offset, gy_offset, gz_offset;

String bth_rx;

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


// read potentiometer data of each finger
void finger() {
  static uint32_t timer_sampling;
  static uint32_t timer_init;
  static uint8_t init_step = 0;
  if (timer_sampling <= millis())
  {
    for (int i = 14; i <= 18; i++)
    {
      if (i < 18)
        sampling[i - 14] += analogRead(i); // read data of each finger
      else
        sampling[i - 14] += analogRead(A6);  // Read data of little finger. I2C uses A4 and A5 ports, therefore, it cannot read continuously starting from A0
      sampling[i - 14] = sampling[i - 14] / 2.0; // obtain the average value between the previous and current measurement values
      data[i - 14 ] = float_map( sampling[i - 14],min_list[i - 14], max_list[i - 14], 2500, 500); // Map the measured value to 500-2500, with 500 for making a fist and 2500 for opening the robotic hand
      data[i - 14] = data[i - 14] > 2500 ? 2500 : data[i - 14];  // limit the maximum value to 2500
      data[i - 14] = data[i - 14] < 500 ? 500 : data[ i - 14];   // limit the minimum value to 500
    }
    timer_sampling = millis() + 10;
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
        Serial.print("max_list:");
        for (int i = 14; i <= 18; i++)
        {
          max_list[i - 14] = sampling[i - 14];
          Serial.print(max_list[i - 14]);
          Serial.print("-");
        }
        Serial.println();
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
        Serial.print("min_list:");
        for (int i = 14; i <= 18; i++)
        {
          min_list[i - 14] = sampling[i - 14];
          Serial.print(min_list[i - 14]);
          Serial.print("-");
        }
        Serial.println();
        //lsc.runActionGroup(0, 1);
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
float radianX_last; // the final obtained X-axis inclination angle
float radianY_last; // the final obtained Y-axis inclination angle


// update data of inclination sensor
void update_mpu6050()
{
  static uint32_t timer_u;
  if (timer_u < millis())
  {
    // put your main code here, to run repeatedly:
    timer_u = millis() + 20;
    accelgyro.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

    ax0 = ((float)(ax)) * 0.3 + ax0 * 0.7;  // filter the read value
    ay0 = ((float)(ay)) * 0.3 + ay0 * 0.7;
    az0 = ((float)(az)) * 0.3 + az0 * 0.7;
    ax1 = (ax0 - ax_offset) /  8192.0;  // calibrate and convert to the multiples of the gravity acceleration
    ay1 = (ay0 - ay_offset) /  8192.0;
    az1 = (az0 - az_offset) /  8192.0;

    gx0 = ((float)(gx)) * 0.3 + gx0 * 0.7;  // filter the read value of angular velocity
    gy0 = ((float)(gy)) * 0.3 + gy0 * 0.7;
    gz0 = ((float)(gz)) * 0.3 + gz0 * 0.7;
    gx1 = (gx0 - gx_offset);  // calibrate angular velocity
    gy1 = (gy0 - gy_offset);
    gz1 = (gz0 - gz_offset);


    // complementary calculation for x-axis inclination angle
    radianX = atan2(ay1, az1);
    radianX = radianX * 180.0 / 3.1415926;
    float radian_temp = (float)(gx1) / 16.4 * 0.02;
    radianX_last = 0.8 * (radianX_last + radian_temp) + (-radianX) * 0.2;

    // complementary calculation for y-axis inclination angle
    radianY = atan2(ax1, az1);
    radianY = radianY * 180.0 / 3.1415926;
    radian_temp = (float)(gy1) / 16.4 * 0.01;
    radianY_last = 0.8 * (radianY_last + radian_temp) + (-radianY) * 0.2;
  }
}

// print data
void print_data()
{
  set_leds(true, true, true, true, true);
  for (int i = 14; i <= 18; i++)
    {
      Serial.print(data[i - 14]);
      Serial.print("  ");
      // Serial.print(float_map(min_list[i-14], max_list[i-14], 500,2500,sampling[i-14]));
    }
    //Serial.println();
    Serial.print("AX: ");
    Serial.print(ax);
    Serial.print(" AY: ");
    Serial.print(ay);
    Serial.print(" AZ: ");
    Serial.print(az);
    Serial.print(" GX: ");
    Serial.print(gx);
    Serial.print(" GY: ");
    Serial.print(gy);
    Serial.print(" GZ: ");
    Serial.println(gz);
  set_leds(false, false, false, false, false);
}

int mode = 0;
bool key_state = false;


void actions() {
  if (turn_on)
    return;
  if (Serial.available()) { // Update HC-08 module
    String str = Serial.readString();
    Serial.println(str);
    if (str.startsWith("AT")) {
      Bth.print(str);
      delay(150);
      bth_rx = Bth.readString();
      Serial.println(bth_rx);
      Bth.flush();
    }
    else if (str.equals("PRINT")) {
      print_data();
    } else if (str.equals("POS_R")) {
      reset_offsets();
    } else if (str.startsWith("LED") && str.length() > 6) {
      set_leds(str.charAt(3) == '1', str.charAt(4) == '1', str.charAt(5) == '1', str.charAt(6) == '1', str.charAt(7) == '1');
    }
  }
  // if K3 button is pressed 
  if(key_state == true && digitalRead(7) == true)
  {
    delay(30);
    if(digitalRead(7) == true)
      key_state = false;
  }
  if (digitalRead(7) == false && key_state == false)
  {
    delay(30);
    // If K3 is pressed, print debug information
    if (digitalRead(7) == false)
    {
      key_state = true;
      print_data();
      if (mode == 5)
      {
        mode = 0;
      }
      else
        mode++;
    }
  }
}

void loop() {
  //return;
  finger();  // update data of finger potentiometers 
  update_mpu6050();  // update data of inclination sensor 

  actions();

  
  //print_data();  // printing sensor data facilitates debugging 
}
