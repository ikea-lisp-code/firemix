import logging

from PySide import QtCore

from core.mixer import Mixer
from core.networking import Networking
from core.scene_loader import SceneLoader
from lib.settings import Settings
from lib.scene import Scene
from lib.plugin_loader import PluginLoader
from lib.aubio_connector import AubioConnector
from lib.osc_server import OscServer
from lib.buffer_utils import BufferUtils
from lib.layer import Layer
from lib.playlist import Playlist

log = logging.getLogger("firemix")


class FireMixApp(QtCore.QThread):
    """
    Main logic of FireMix.  Operates the mixer tick loop.
    """
    def __init__(self, args, parent=None):
        self._running = False
        self.args = args
        self.settings = Settings()
        self.net = Networking(self)
        BufferUtils.set_app(self)
        self.scene = Scene(self)
        self.plugins = PluginLoader()
        self.mixer = Mixer(self)

        # Create the default layer.
        default_playlist = Playlist(self, self.args.playlist, 'last_playlist')
        default_layer = Layer(self, 'default')
        default_layer.set_playlist(default_playlist)
        self.mixer.add_layer(default_layer)

        if self.args.speech_layer:
            speech_playlist = Playlist(self, self.args.speech_playlist, 'last_speech_playlist')
            speech_layer = Layer(self, 'speech')
            speech_layer.set_playlist(speech_playlist)
            self.mixer.add_layer(speech_layer)

        self.scene.warmup()

        self.aubio_connector = None
        if not self.args.noaudio:
            self.aubio_connector = AubioConnector()
            self.aubio_connector.onset_detected.connect(self.mixer.onset_detected)

        self.osc_server = None
        if not self.args.noosc:
            self.osc_server = OscServer(
                self.args.osc_port, self.args.mixxx_osc_port, self.mixer)
            self.osc_server.start()

        if self.args.preset:
            log.info("Setting constant preset %s" % args.preset)
            self.mixer.set_constant_preset(args.preset)

        QtCore.QThread.__init__(self, parent)

    def run(self):
        self._running = True
        self.mixer.run()

    def stop(self):
        self._running = False
        self.mixer.stop()
        self.mixer.save()
        self.settings.save()
