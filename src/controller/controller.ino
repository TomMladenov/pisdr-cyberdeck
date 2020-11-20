#include <Wire.h>

#define SLAVE_ADDRESS   0x04

#define PARAM_ID_TIME   0x54
#define PARAM_ID_STDTM  0x53


volatile boolean receiveFlag = false;
char command[32];
int crc8;

char command_type;
char CMD_SET = 'S';
char CMD_GET = 'G';

int parameter_id;
bool debug = false;


int     status;
bool    b_status_rf1, b_status_rf2, b_status_audio, b_status_gps, b_status_imu, b_status_wlan, b_status_usb, b_muted;
int     volume;

float   frequency;
int     mode;

float   f_gps_lat, f_gps_lon, f_gps_alt, f_gps_time;
int     year, month, day, hour, minute, second;


void setup() {
  Wire.begin(SLAVE_ADDRESS);
  Wire.onReceive(receiveEvent);

  Serial.begin(115200);
  Serial.println("Ready!");

}

void loop() {

  Serial.print(hour);
  Serial.print(":");
  Serial.print(minute);
  Serial.print(":");
  Serial.print(second);
  Serial.print(" UTC   ");

  Serial.print(day);

  Serial.print("/");
  Serial.print(month);
  Serial.print("/");
  Serial.println(2000 + year);

  delay(1000);
}


void decodeTimePacket(char command[]) {
  hour = command[2];
  minute = command[3];
  second = command[4];

  year = command[5];
  month = command[6];
  day = command[7];
}


void decodeStandardTelemetryPacket(char command[]) {
  hour = command[2];
  minute = command[3];
  second = command[4];

  year = command[5];
  month = command[6];
  day = command[7];
}





void receiveEvent(int howMany) {

  for (int i = 0; i < howMany; i++) {
    command[i] = Wire.read();
    command[i + 1] = '\0';
  }

  command_type = command[0];
  parameter_id = command[1];

  if (debug == true) {
    for (size_t i = 0; i < sizeof(command) - 1; i++)
    {
      Serial.print(static_cast<unsigned int>(command[i]), HEX);
    }

    Serial.println(' ');

  }

  switch (parameter_id) {
    case PARAM_ID_TIME:
      decodeTimePacket(command);
      break;
    case PARAM_ID_STDTM:
      decodeStandardTelemetryPacket(command);
      break;
    default:
      // statements
      break;
  }

}
