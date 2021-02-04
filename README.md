# Raspberry Pi SDR Cyberdeck

This repository contains the software for the [Raspberry Pi SDR Cyberdeck project](https://hackaday.io/project/174301-raspberry-pi-sdr-cyberdeck)

![alt text](./doc/img/box_outlined.jpg)

The purpose of the software is to provide an easy-to-use interface for starting/stopping software and allow several control clients to connect and
execute actions and fetch via HTTP methods. The latter is done by using [FastAPI](https://fastapi.tiangolo.com/).


## Setup

### Hardware

Schematics are available at the dedicated [Hackaday page](https://hackaday.io/project/174301-raspberry-pi-sdr-cyberdeck).
A minimal setup consists of a raspberry Pi and the 7" Official touch display.

If you will be using 2x RTL-SDRs similar to the original Hackaday project, then it is required to give them both unique serial numbers 'rf1' and 'rf2' in order for them to be uniquely identified.
```
rtl_eeprom -d 0 -s 'rf1'
rtl_eeprom -d 1 -s 'rf2'
```

### Software

![alt text](./doc/img/logos.png)

The Raspberry Pi SDR cyberdeck runs on a software framework with at it's core an ASGI (Asynchronous Server Gateway Interface), in this case uvicorn. The ASGI interface connects to FastAPI which performs the function invocations in the Python threads which control the Devices, Processes and Applications. This allows for easy system manipulation via HTTP1.1 GET/PUT/POSTS methods. The Python threads controlling the processes can range from a commandline decoder to decode APRS via an audio interface, through to starting a VNC session or starting navigation/mapping software. The intention is to make complex application flow, configuration and control easily accessible via the Cyberdeck API interface (which performs HTTP requests to the server), therefore eliminating local commandline interaction with the system. In parallel system data is dumped to an influxdb database, and exposed via Grafana, allowing easy system monitoring over longer periods of time.

```
pip3 install -r doc/requirements.txt
```

Clone the following repositories and follow individual installation instructions:
- [uhubctl](https://github.com/mvp/uhubctl)
- [dumpvdl2](https://github.com/szpajder/dumpvdl2)
- [dump1090](https://github.com/antirez/dump1090)
- [acarsdec](https://github.com/TLeconte/acarsdec)
- [rtl-ais](https://github.com/dgiardini/rtl-ais)
- [rtl-sdr](https://github.com/sysrun/rtl-sdr) (extended version to use a UDP control port and other features)


Example Raspberry config file [here](doc/config.txt):


Every subsystem is defined by either:
- device (anything that needs polling over I2C, input pins, etc)
- process (anything that requires an input device, either RF or alsa)
- application (anything that has a GUI and does not fall in above 2 classes)

The latter are functionally described in the server [config.ini](src/api/config.ini) file:

```
[battery]
s_id = battery
s_name = Battery
s_type = device
s_level_i2c_addr = 0x48
i_level_polling_period = 1

s_temp1_sensor = 28-00000a2efb67
s_temp2_sensor =  28-00000a2ece8c
i_temp_polling_period = 5

i_pd_threshold = 3000
i_capacity = 15600
i_capacity_wh = 57
s_model = Anker Powercore

[rtltcp1]
s_id = rtltcp1
s_name = RF TCP SERVER 1
s_type = process
s_host = 0.0.0.0
i_port = 5002
i_freq = 135000000
i_gain = 48
i_samprate = 1024000
s_device = rf1
b_directsamp = no
b_bias = no
```

To add a subsystem:
- Add section in the [config.ini](src/api/config.ini) file
- Define the system in [systems.py](src/api/systems.py) by subclassing either device, process or application
- Instantiate it in [server.py](src/api/server.py) and pass it the unique INI-section
- Add any additional get/put methods in [main.py](src/api/main.py) for the REST API


### Operations

1) Starting the server locally on the Rpi:
```
cd src/api
python3 main.py
```
The ASGI server runs on 0.0.0.0, and will accept connections on any interface.


2) Start one (or several) clients with IP a reachable interface on the Rpi (or 127.0.0.1 for a local conrol client):
```
cd src/api
python3 gui.py -i {YOUR_IP_HERE}
```

3) A dry-run test can be done from the browser by testing out some HTTP methods at:
```
http://{YOUR_IP_HERE}:5000/docs
```
