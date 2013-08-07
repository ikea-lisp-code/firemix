# Daemon running on the Raspberry Pi for reading Firemix UDP packets
# and writing to serial.

import logging as log
import signal
import sys
from PySide import QtCore
from PySide import QtNetwork

try:
    import serial
except ImportError as err: 
    sys.stderr.write("Error: failed to import module ({})".format(err))


class DMXDaemon(QtCore.QObject):

    ready_to_read = QtCore.Signal()

    def __init__(self, serial_port):
        super(DMXDaemon, self).__init__()
        self.__socket = None
        self.__serial = serial_port
        
    def init_socket(self):
        self.__socket = QtNetwork.QUdpSocket(self)
        self.__socket.readyRead.connect(self.read_datagrams)
        self.__socket.bind(3020, QtNetwork.QUdpSocket.ShareAddress | QtNetwork.QUdpSocket.ReuseAddressHint)
        log.info("Listening on UDP 3020")
    
    @QtCore.Slot()
    def read_datagrams(self):
        while self.__socket.hasPendingDatagrams():
            datagram = QtCore.QByteArray()
            datagram.resize(self.__socket.pendingDatagramSize())
            (datagram, sender, sport) = self.__socket.readDatagram(datagram.size())
            packet = [ord(c) for c in datagram.data()]
            self.process_command(packet)

    def process_command(self, packet):
        strand = packet[0]
        cmd = packet[1]
        datalen = (packet[3] << 8) + packet[2]
        data = packet[4:]
        # Bulk Strand Set
        if cmd == 0x10 or cmd == 0x20:
            assert datalen <= 512
            self.__serial.send_dmx(strand, bytearray(data))
        elif cmd < 0x27 and cmd > 0x20:
            print hex(cmd)
            raise NotImplementedError
        else: 
            raise NotImplementedError


class DMXSerialRenderer(object):
    """ DMXSerialRenderer provides a renderer interface to a custom DMX shield 
    using the RaspberryPi serial port.
    TODO: The baudrate on the Pi currently ceilings at 115200 baud. Change back to 
    250000 baud when fixed on the Pi-side.
    """ 

    __dmx_buffer_size = 512
    __default_channel_val = 0
    __device_name = "/dev/ttyAMA0"
    __baud_rateHz = 115200
    __timeout = 3.
    __bytesize = serial.EIGHTBITS
    __parity = serial.PARITY_NONE
    __stopbits = serial.STOPBITS_TWO

    __slots__ = {'__port'}
    
    def __init__(self):
        super(DMXSerialRenderer, self).__init__()
        self.__port = serial.Serial(port = DMXSerialRenderer.__device_name)
        self.__port.baudrate = DMXSerialRenderer.__baud_rateHz
        self.__port.bytesize = DMXSerialRenderer.__bytesize
        self.__port.parity = DMXSerialRenderer.__parity
        self.__port.stopbits = DMXSerialRenderer.__stopbits
        self.__port.timeout = DMXSerialRenderer.__timeout

    def send_dmx(self, universe, buf):
        """ Sends the DMX packet over serial.
        """ 
        self.__port.baudrate = DMXSerialRenderer.__baud_rateHz/2
        self.__port.write(chr(0))
        self.__port.baudrate = DMXSerialRenderer.__baud_rateHz
        self.__port.write(chr(0))
        self.__port.write(buf)

    def close(self):
        """ Close the serial port.
        """
        self.__port.close()
        
    def __del__(self):
        self.close()

    def __repr__(self):
        return "DMXSerialRenderer"


def sigint_handler(signal, frame):
    global app
    app.exit()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    app = QtCore.QCoreApplication(["DMXDaemon"])
    print "Press Ctrl-C to quit"
    serial_port = DMXSerialRenderer()
    nc = DMXDaemon(serial_port)
    nc.init_socket()
    sys.exit(app.exec_())
