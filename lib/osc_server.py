import liblo
import logging
import re
import time
import os
from PySide import QtCore, QtNetwork

log = logging.getLogger("firemix.lib.osc_server")

def restricted_range_float_handler(path, min_value, max_value):
    def decorate(function):
        def handler(self, path, args, types, src):
            if min_value <= args[0] <= max_value:
                return function(self, args[0])
        return liblo.make_method(path, 'f')(handler)
    return decorate

def string_handler(path):
    def decorate(function):
        def handler(self, path, args, types, src):
            return function(self, args[0])
        return liblo.make_method(path, 's')(handler)
    return decorate

def no_arg_handler(path):
    def decorate(function):
        def handler(self, path, args, types, src):
            return function(self)
        return liblo.make_method(path, '')(handler)
    return decorate

class OscServer(liblo.ServerThread):

    def __init__(self, port, mixxx_port, mixer):
        super(OscServer, self).__init__(port)
        self.features_seen = set()
        self.mixer = mixer
        self.mixxx_address = liblo.Address(mixxx_port)

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
        self.mixer.feature_received(feature)

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
        self.mixer.feature_received(feature)

    @restricted_range_float_handler('/firemix/global_dimmer', 0.0, 1.0)
    def set_global_dimmer(self, value):
        print 'set_global_dimmer', value
        self.mixer.set_global_dimmer(value)

    @restricted_range_float_handler('/firemix/global_speed', 0.0, 10.0)
    def set_global_speed(self, value):
        self.mixer.set_global_speed(value)


    @restricted_range_float_handler('/firemix/preset_duration', 0.0, 60.0)
    def set_preset_duration(self, value):
        self.mixer.set_preset_duration(value)

    @restricted_range_float_handler('/firemix/transition_duration', 0.0, 60.0)
    def set_transition_duration(self, value):
        self.mixer.set_transition_duration(value)

    @no_arg_handler('/firemix/next_preset')
    def next_preset(self):
        self.mixer.next()

    @no_arg_handler('/firemix/previous_preset')
    def prev_preset(self):
        self.mixer.prev()

    @no_arg_handler('/firemix/start_transition')
    def start_transition(self):
        self.mixer.start_transition()

    @no_arg_handler('/firemix/toggle_pause')
    def toggle_pause(self):
        self.mixer.pause(not self.mixer.is_paused())

    @no_arg_handler('/firemix/toggle_freeze')
    def toggle_freeze(self):
        self.mixer.freeze(not self.mixer.is_frozen())

    @string_handler('/firemix/load_playlist')
    def load_playlist(self, playlist_name):
        paused = self.mixer.is_paused()
        self.mixer.stop()
        old_name = self.mixer._playlist.filename

        playlist_path = os.path.join(os.getcwd(), "data", "playlists",
                                     ''.join((playlist_name, '.json')))
        self.mixer._playlist.set_filename(playlist_path)

        if not self.mixer._playlist.open():
            self.mixer._playlist.set_filename(old_name)
        self.mixer.run()
        self.mixer.pause(paused)

    @liblo.make_method('/mixxx/control/set', None)
    def mixxx_control_set(self, path, args, types, src):
        if not re.match('^(sd)+$', types):
            return

        # Simply re-broadcast to Mixxx.
        liblo.send(self.mixxx_address, '/control/set', *zip(types, args))

    def start(self):
        super(OscServer, self).start()
        log.info("OSC server listening on port %d.", self.get_port())

    def broadcast_mixxx_message(self, path, args):
        liblo.send(self.mixxx_address, path, *args)

    def broadcast_mixxx_control_updates(self, args):
        values = []
        for control, value in args:
            values.append(('s', control))
            values.append(('d', value))
        self.broadcast_mixxx_message('/control/set', values)
