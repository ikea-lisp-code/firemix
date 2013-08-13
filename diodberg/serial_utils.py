# Utilities for testing the serial protocol on the Raspberry Pi.

import sys
import time
try:
    import serial
except ImportError as err:
    sys.stderr.write("Error: failed to import module ({})".format(err))


def write_dmx(baudrate = 250000, buf = bytearray([255, 255, 255])):
    """ Simple test routine for DMX-over-serial, with varying baudrates. The buf is
    the DMX address space (0 - 512). 
    TODO: The baudrate on the Pi currently ceilings at 115200 baud. Change back to 
    250000 baud when fixed on the Pi-side.
    """
    assert isinstance(buf, bytearray)
    num_addresses = 512
    assert len(buf) <= num_addresses
    # DMX serial default parameters
    device_name = "/dev/ttyUSB0"
    port = serial.Serial(device_name)
    port.baudrate = baudrate
    port.bytesize = serial.EIGHTBITS
    port.parity = serial.PARITY_NONE
    port.stopbits = serial.STOPBITS_TWO
    port.timeout = 3.
    # Write break and mark-after-break
    port.baudrate = baudrate/2
    port.write(chr(0))
    # Write start and then values to address 0, 1, 2 
    # on universe 0
    port.baudrate = baudrate
    port.write(chr(0))
    port.write(buf)
    port.close()


def probe(num_addresses = 100, sleep = 5):
    write_dmx(buf = bytearray([0]*512))
    empty = bytearray([255]*512)
    for i in xrange(num_addresses):
        if i % 3 == 0:
            val = bytearray(empty)
            val[i] = 0
            write_dmx(buf = val)
            print "Address: ", str(i/3.)
            time.sleep(sleep)


if __name__ == "__main__":
    probe()
