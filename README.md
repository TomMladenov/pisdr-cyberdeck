# Raspberry Pi SDR Cyberdeck

This repository contains the software for the [Raspberry Pi SDR Cyberdeck project](https://hackaday.io/project/174301-raspberry-pi-sdr-cyberdeck)

The purpose of the software is to provide an easy-to-use interface for starting/stopping software of interest as
wall as a range of monitoring and BITS (Built in self-test) functions.


## Setup

### Hardware

Schematics are available at the dedicated [Hackaday page](https://hackaday.io/project/174301-raspberry-pi-sdr-cyberdeck).
A minimal setup consists of a raspberry Pi and the 7" Official touch display.

### Software

Install the following software packages on the Raspberry pi via apt-get:
- GQRX
- OpenCPN
- xastir
- xdotool
- fldigi
- wsjtx
- rtl-sdr


Install the following python packages via pip:
- [PyQt5](https://pypi.org/project/PyQt5/)
- [rpi-backlight](https://pypi.org/project/rpi-backlight/)
- [mgrs](https://pypi.org/project/mgrs/)
- [adafruit-circuitpython-ina219](https://pypi.org/project/adafruit-circuitpython-ina219/)

or use the `requirements.txt` file:
```
pip3 install -r requirements.txt
```

Clone the following repositories into `/home/pi/git/` and follow individual installation instructions:
- [uhubctl](https://github.com/mvp/uhubctl)
- [dumpvdl2](https://github.com/szpajder/dumpvdl2)
- [dump1090](https://github.com/antirez/dump1090)
- [uwave-eas](https://github.com/UWave/uwave-eas)
- [acarsdec](https://github.com/TLeconte/acarsdec)
- [rtl-ais](https://github.com/dgiardini/rtl-ais)
- [rtl-sdr](https://github.com/sysrun/rtl-sdr) (extended version to use a UDP control port and other features)


Add the following entries to `/boot/config.txt`:
```
[all]
lcd_rotate=0
disable_splash=1
dtparam=act_led_trigger=none
dtparam=act_led_activelow=on
dtoverlay=w1-gpio
gpiopin=4
enable_uart=1
gpio=7=pd
```


Add a line to `/etc/xdg/lxsession/LXDE-pi/autostart` for starting application at boot:
```
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@/usr/bin/python3 /home/pi/git/pisdr-cyberdeck/src/main.py
```
