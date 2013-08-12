import liblo
import logging
import re
import time
from PySide import QtCore, QtNetwork

log = logging.getLogger("firemix.lib.osc_server")

class OscServer(liblo.ServerThread):

    class Notifier(QtCore.QObject):
        feature_received = QtCore.Signal(dict)

        def __init__(self):
            super(OscServer.Notifier, self).__init__()

    def __init__(self, port):
        super(OscServer, self).__init__(port)
        self.notifier = OscServer.Notifier()
        self.features_seen = set()

    @liblo.make_method(None, 'ff')
    def float_float_message_received(self, path, args, types, src):
        if not path.startswith('/'):
            return
        components = path[1:].split('/')

        if len(components) != 2:
            log.error("Couldn't understand message: %s %s %s %s", path, args, types, src)
            return

        message_time, value = args

        if components[1] not in self.features_seen:
            self.features_seen.add(components[1])
            print "New feature seen:", components[1]


        feature = {
            'group': components[0],
            'feature': components[1],
            'time': message_time,
            'value': value,
            'time_received': time.time(),
        }

        #print "received unknown message", path, args, types, src
        self.notifier.feature_received.emit(feature)

    @liblo.make_method(None, 'fT')
    @liblo.make_method(None, 'fF')
    def float_bool_message_received(self, path, args, types, src):
        if not path.startswith('/'):
            return
        components = path[1:].split('/')

        if len(components) != 2:
            log.error("Couldn't understand message: %s %s %s %s", path, args, types, src)
            return

        message_time, value = args

        feature = {
            'group': components[0],
            'feature': components[1],
            'time': message_time,
            'value': value,
            'time_received': time.time(),
        }

        self.notifier.feature_received.emit(feature)

    def start(self):
        super(OscServer, self).start()
        log.info("OSC server listening on port %d.", self.get_port())
