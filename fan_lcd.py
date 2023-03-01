from luma.core import cmdline, error
import time
import datetime
from luma.core.render import canvas
import sys
import subprocess
import RPi.GPIO as GPIO
import time
import subprocess as sp
import socket

GPIO.setwarnings(False)

# initializing GPIO, setting mode to BOARD.
# Default pin of fan is physical pin 8, GPIO14
Fan = 8
GPIO.setmode(GPIO.BOARD)
GPIO.setup(Fan, GPIO.OUT)

fan = GPIO.PWM(Fan, 50)
fan.start(0)


def display_settings(device, args):
    """
    Display a short summary of the settings.

    :rtype: str
    """
    iface = ''
    display_types = cmdline.get_display_types()
    if args.display not in display_types['emulator']:
        iface = f'Interface: {args.interface}\n'

    lib_name = cmdline.get_library_for_display_type(args.display)
    if lib_name is not None:
        lib_version = cmdline.get_library_version(lib_name)
    else:
        lib_name = lib_version = 'unknown'

    import luma.core
    version = f'luma.{lib_name} {lib_version} (luma.core {luma.core.__version__})'

    return f'Version: {version}\nDisplay: {args.display}\n{iface}Dimensions: {device.width} x {device.height}\n{"-" * 60}'


def get_device(actual_args=None):
    """
    Create device from command-line arguments and return it.
    """
    if actual_args is None:
        actual_args = sys.argv[1:]
    parser = cmdline.create_parser(description='luma.examples arguments')
    args = parser.parse_args(actual_args)

    if args.config:
        # load config from file
        config = cmdline.load_config(args.config)
        args = parser.parse_args(config + actual_args)

    # create device
    try:
        device = cmdline.create_device(args)
        print(display_settings(device, args))
        return device

    except error.Error as e:
        parser.error(e)
        return None


def get_temp():  # Function to read in the CPU temperature and return it as a float in degrees celcius
    output = sp.run(['vcgencmd', 'measure_temp'], capture_output=True)
    temp_str = output.stdout.decode()
    try:
        return float(temp_str.split('=')[1].split('\'')[0])
    except (IndexError, ValueError):
        raise RuntimeError('Could not get temperature')


def internet(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        return False


def server(host="192.168.1.100", port=8080, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        return False


def main():
    print(f"initial temp {get_temp()} degree")
    speed = 100
    device = get_device()

    while True:

        # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
        cmd = "hostname -I | cut -d\' \' -f1"
        IP = subprocess.check_output(cmd, shell=True)
        cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell=True)
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
        MemUsage = subprocess.check_output(cmd, shell=True)
        cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
        Disk = subprocess.check_output(cmd, shell=True)
        temp = get_temp()
        serverIotech = server()
        if serverIotech is True:
            serverIotech = "on"
        else:
            serverIotech = "off"

        with canvas(device) as draw:
            x = 1
            top = 1
            draw.text((x, top), "IP: " + str(IP).split("b'")[1], fill=255)
            draw.text((x, top + 9), "Wifi conn: " + str(internet()) + "", fill=255)
            draw.text((x, top + 17), str(CPU).split("b'")[1], fill=255)
            draw.text((x, top + 27), str(MemUsage).split("b'")[1], fill=255)
            draw.text((x, top + 36), str(Disk).split("b'")[1], fill=255)
            draw.text((x, top + 45), "Fan: " + str(speed) + "%. " + "Temp: " + str(temp) + "C", fill=255)

            if temp > 42:
                speed = 100
            elif 40 < temp < 42:
                pass
            elif 35 < temp < 40:
                speed = 75
            elif 33 < temp < 35:
                pass
            elif 30 < temp < 33:
                speed = 25
            else:
                speed = 10

            draw.text((x, top + 53), "Iotech server is " + serverIotech, fill=255)
            # print(f"temp: {temp}; speed: {speed}%")

        fan.ChangeDutyCycle(speed)
        time.sleep(10)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
