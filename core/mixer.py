import logging
from collections import defaultdict
import threading
import time
import numpy as np

from profilehooks import profile

USE_YAPPI = True
try:
    import yappi
except ImportError:
    USE_YAPPI = False

from PySide import QtCore

from lib.buffer_utils import BufferUtils
from lib.audio_emitter import AudioEmitter
from lib.colors import blend_to_buffer

log = logging.getLogger("firemix.core.mixer")


class Mixer(QtCore.QObject):
    """
    Mixer is the brains of FireMix.  It handles the playback of presets
    and the generation of the final command stream to send to the output
    device(s).
    """
    def __init__(self, app):
        super(Mixer, self).__init__()
        self._app = app
        self._net = app.net
        self._scene = app.scene
        self._tick_rate = self._app.settings.get('mixer')['tick-rate']
        self._tick_timer = None
        self._running = False
        self._enable_rendering = True
        self._main_buffer = None
        self._tick_time_data = dict()
        self._num_frames = 0
        self._last_frame_time = 0.0
        self._start_time = 0.0
        self._stop_time = 0.0
        self._enable_profiling = self._app.args.profile
        self._paused = self._app.settings.get('mixer').get('paused', False)
        self._frozen = False
        self._last_onset_time = 0.0
        self._onset_holdoff = self._app.settings.get('mixer')['onset-holdoff']
        self._onset = False
        self._reset_onset = False
        self._global_dimmer = 1.0
        self._global_speed = 1.0
        self._render_in_progress = False
        self._last_tick_time = time.time()
        self._audio_emitters_by_group = {}
        self._layers = []

        if self._app.args.yappi and USE_YAPPI:
            yappi.start()

        if not self._scene:
            log.warn("No scene assigned to mixer.  Preset rendering and transitions are disabled.")
            self._enable_rendering = False
        else:
            log.info("Warming up BufferUtils cache...")
            BufferUtils.init()
            log.info("Completed BufferUtils cache warmup")

            log.info("Initializing preset rendering buffer")
            fh = self._scene.fixture_hierarchy()

            self._main_buffer = BufferUtils.create_buffer()

    def save(self):
        for layer in self._layers:
            layer.save()

    def run(self):
        if not self._running:
            self._tick_rate = self._app.settings.get('mixer')['tick-rate']
            self._tick_timer = threading.Timer(1.0 / self._tick_rate, self.on_tick_timer)
            self._tick_timer.start()
            self._running = True
            self._num_frames = 0
            self._start_time = self._last_frame_time = time.time()
            self.reset_output_buffer()

            for layer in self._layers:
                layer.reset()

    def stop(self):
        self._running = False
        self._tick_timer.cancel()
        self._stop_time = time.time()

        if self._app.args.yappi and USE_YAPPI:
            yappi.print_stats(sort_type=yappi.SORTTYPE_TSUB, limit=15, thread_stats_on=False)

    def pause(self, pause=True):
        self._paused = pause
        self._app.settings.get('mixer')['paused'] = pause

    def is_paused(self):
        return self._paused

    @QtCore.Slot()
    def onset_detected(self):
        t = time.clock()
        if (t - self._last_onset_time) > self._onset_holdoff:
            self._last_onset_time = t
            self._onset = True

    def audio_emitter(self, group):
        audio_emitter = self._audio_emitters_by_group.get(group, None)
        if audio_emitter is None:
            audio_emitter = AudioEmitter(group)
            self._audio_emitters_by_group[group] = audio_emitter
            cx, cy = self._scene.center_point()
            audio_emitter.set_target_position((cx, cy, 0))
        return audio_emitter

    @QtCore.Slot(dict)
    def feature_received(self, feature):
        feature_group = feature.get('group', None)
        if feature_group is None:
            log.error('Received feature without a group: %s. Ignoring.', feature)
            return

        feature_name = feature.get('feature', None)
        if feature_name is None:
            log.error('Received feature without a name: %s. Ignoring.', feature)
            return

        audio_emitter = self.audio_emitter(feature_group)
        audio_emitter.on_feature_update(feature_name, feature)

        # Maintain legacy onset behavior.
        if feature['feature'] == 'onset' and feature['value']:
            t = time.clock()
            if (t - self._last_onset_time) > self._onset_holdoff:
                self._onset = True
                self._last_onset_time = t

        for layer in self._layers:
            layer.feature_received(feature)

    def set_global_dimmer(self, dimmer):
        self._global_dimmer = dimmer

    def set_global_speed(self, speed):
        self._global_speed = speed

    def freeze(self, freeze=True):
        self._frozen = freeze

    def is_frozen(self):
        return self._frozen

    @profile
    def on_tick_timer(self):
        start = time.clock()
        self._render_in_progress = True
        self.tick()
        self._render_in_progress = False

        dt = (time.clock() - start)
        delay = max(0, (1.0 / self._tick_rate) - dt)
        self._running = self._app._running
        if self._running:
            self._tick_timer = threading.Timer(delay, self.on_tick_timer)
            self._tick_timer.start()

    def set_constant_preset(self, classname):
        self.default_layer()._playlist.clear_playlist()
        self.default_layer()._playlist.add_preset(classname, classname)
        self._paused = True

    def add_layer(self, layer):
        self._layers.append(layer)

    def default_layer(self):
        return self._layers[0]

    def layer_by_name(self, name):
        for layer in self._layers:
            if layer.name == name:
                return layer
        return None

    def get_tick_rate(self):
        return self._tick_rate

    def is_onset(self):
        """
        Called by presets; resets after tick if called during tick
        """
        if self._onset:
            self._reset_onset = True
            return True
        return False

    def tick(self):
        self._num_frames += 1
        now = time.time()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        if self._frozen:
            return

        dt *= self._global_speed

        # Draw every layer to the main buffer.
        output_buffer = self._main_buffer

        if len(self._layers) == 1:
            output_buffer = self._layers[0].draw(dt)
        else:
            # Clear the output buffer.
            output_buffer[:] = (0.0, 0.0, 0.0)

            for layer in self._layers:
                layer_buffer = layer.draw(dt)
                output_buffer = blend_to_buffer(layer_buffer, output_buffer, 0.5, 'overwrite')

        if self._enable_rendering:
            # Apply the global dimmer to output_buffer.
            if self._global_dimmer < 1.0:
                output_buffer.T[1] *= self._global_dimmer

            # Mod hue by 1 (to allow wrap-around) and clamp lightness and
            # saturation to [0, 1].
            output_buffer.T[0] = np.mod(output_buffer.T[0], 1.0)
            np.clip(output_buffer.T[1], 0.0, 1.0, output_buffer.T[1])
            np.clip(output_buffer.T[2], 0.0, 1.0, output_buffer.T[2])

            # Write this buffer to enabled clients.
            if self._net is not None:
                self._net.write_buffer(output_buffer)
        else:
            # TODO(rryan): Make this layer-aware.
            if self._net is not None:
                self._net.write_commands(
                    self.default_layer()._playlist.get_active_preset().get_commands_packed())

        if self._reset_onset:
            self._onset = False
            self._reset_onset = False

        if self._enable_profiling:
            tick_time = (time.time() - self._last_frame_time)
            self._last_frame_time = time.time()
            if tick_time > 0.0:
                index = int((1.0 / tick_time))
                self._tick_time_data[index] = self._tick_time_data.get(index, 0) + 1

        # Update Mixxx with the latest values.
        control_updates = []
        for group, emitter in self._audio_emitters_by_group.iteritems():
            x, y, z = emitter.target_position()
            control_updates.append(('%s,position_x' % group, x))
            control_updates.append(('%s,position_y' % group, y))
            control_updates.append(('%s,position_z' % group, z))
        self._app.osc_server.broadcast_mixxx_control_updates(control_updates)

    def scene(self):
        return self._scene

    def reset_output_buffer(self):
        """
        Clears the output buffer
        """
        self._main_buffer = BufferUtils.create_buffer()
