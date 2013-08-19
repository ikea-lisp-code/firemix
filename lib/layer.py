import math
import random
import logging

from PySide import QtCore

from lib.buffer_utils import BufferUtils

log = logging.getLogger("firemix.lib.layer")

class Layer(QtCore.QObject):

    transition_starting = QtCore.Signal()

    def __init__(self, app, name):
        super(Layer, self).__init__()
        self._app = app
        self._mixer = app.mixer
        self._enable_profiling = self._app.args.profile
        self.name = name
        self._playlist = None
        self._scene = app.scene
        self._main_buffer = None
        self._secondary_buffer = None
        self._in_transition = False
        self._transition = None
        self.transition_progress = 0.0
        self._start_transition = False
        self._transition_list = []
        self._transition_duration = self._app.settings.get('mixer')['transition-duration']
        self._transition_slop = self._app.settings.get('mixer')['transition-slop']
        self._elapsed = 0
        self._duration = self._app.settings.get('mixer')['preset-duration']

        # Load transitions
        self.set_transition_mode(self._app.settings.get('mixer')['transition'])

        if not self._scene:
            pass
        else:
            self._main_buffer = BufferUtils.create_buffer()
            self._secondary_buffer = BufferUtils.create_buffer()

    def save(self):
        self._playlist.save()

    def reset(self):
        self._main_buffer = BufferUtils.create_buffer()
        self._secondary_buffer = BufferUtils.create_buffer()

    def set_playlist(self, playlist):
        self._playlist = playlist

    def playlist(self):
        return self._playlist

    def set_preset_duration(self, duration):
        if duration >= 0.0:
            self._duration = duration
            return True
        else:
            log.warn("Preset duration must be positive or zero.")
            return False

    def get_preset_duration(self):
        return self._duration

    def set_transition_duration(self, duration):
        if duration >= 0.0:
            self._transition_duration = duration
            return True
        else:
            log.warn("Transition duration must be positive or zero.")
            return False

    def get_transition_duration(self):
        return self._transition_duration

    def next(self):
        #TODO: Fix this after the Playlist merge
        if len(self._playlist) == 0:
            return

        self.start_transition(self._playlist.get_preset_relative_to_active(1))

    def prev(self):
        #TODO: Fix this after the Playlist merge
        if len(self._playlist) == 0:
            return
        self.start_transition(self._playlist.get_preset_relative_to_active(-1))

    def start_transition(self, next=None):
        """
        Starts a transition.  If a name is given for Next, it will be the
        endpoint of the transition.
        """
        # Don't transition if we only have one preset.
        if len(self._playlist) <= 1:
            return

        if next is not None:
            self._playlist.set_next_preset_by_name(next)

        self._in_transition = True
        self._start_transition = True
        self._elapsed = 0.0
        self.transition_starting.emit()

    def cancel_transition(self):
        self._start_transition = False
        if self._in_transition:
            self._in_transition = False

    def get_transition_by_name(self, name):
        if not name or name == "Cut":
            return None

        if name == "Random":
            self.build_random_transition_list()
            return self.get_next_transition()

        tl = [c for c in self._app.plugins.get('Transition') if str(c(None)) == name]

        if len(tl) == 1:
            return tl[0](self._app)
        else:
            log.error("Transition %s is not loaded!" % name)
            return None

    def set_transition_mode(self, name):
        if not self._in_transition:
            self._transition = self.get_transition_by_name(name)
        return True

    def build_random_transition_list(self):
        self._transition_list = [c for c in self._app.plugins.get('Transition')]
        random.shuffle(self._transition_list)

    def get_next_transition(self):
        if len(self._transition_list) == 0:
            self.build_random_transition_list()
        self._transition = self._transition_list.pop()(self._app)
        self._transition.setup()

    def feature_received(self, feature):
        # Notify active preset of feature.
        active_preset = self._playlist.get_active_preset()
        if active_preset:
            active_preset.on_feature(feature)

    def draw(self, dt):
        if len(self._playlist) == 0:
            self._main_buffer *= (0.0, 0.0, 0.0)
            return self._main_buffer

        self._elapsed += dt

        active_preset = self._playlist.get_active_preset()
        active_index = self._playlist.get_active_index()

        next_preset = self._playlist.get_next_preset()
        next_index = self._playlist.get_next_index()

        active_preset.clear_commands()
        active_preset.tick(dt)

        # Handle transition by rendering both the active and the next preset,
        # and blending them together.
        if self._in_transition:
            if self._start_transition:
                self._start_transition = False
                if self._app.settings.get('mixer')['transition'] == "Random":
                    self.get_next_transition()
                if self._transition:
                    self._transition.reset()
                next_preset._reset()
                self._secondary_buffer = BufferUtils.create_buffer()

            if self._transition_duration > 0.0 and self._transition is not None:
                if not self._mixer.is_paused():
                    self.transition_progress = self._elapsed / self._transition_duration
            else:
                self.transition_progress = 1.0

            next_preset.clear_commands()
            next_preset.tick(dt)

            # Exit from transition state after the transition duration has
            # elapsed
            if self.transition_progress >= 1.0:
                self._in_transition = False
                # Reset the elapsed time counter so the preset runs for the
                # full duration after the transition
                self._elapsed = 0.0
                self._playlist.advance()
                active_preset = next_preset
                active_index = next_index

        first_preset = self._playlist.get_preset_by_index(active_index)
        if self._in_transition:
            second_preset = self._playlist.get_preset_by_index(next_index)
            mixed_buffer = self.render_presets(
                first_preset, self._main_buffer,
                second_preset, self._secondary_buffer,
                self._in_transition, self._transition,
                self.transition_progress,
                check_for_nan=self._enable_profiling)
        else:
            mixed_buffer = self.render_presets(
                first_preset, self._main_buffer,
                check_for_nan=self._enable_profiling)

        if not self._mixer.is_paused() and (self._elapsed >= self._duration) and active_preset.can_transition() and not self._in_transition:
            if (self._elapsed >= (self._duration + self._transition_slop)) or self._mixer._onset:
                self.start_transition()
                self._elapsed = 0.0

        return mixed_buffer

    def render_presets(self, first_preset, first_buffer,
                       second_preset=None, second_buffer=None,
                       in_transition=False, transition=None,
                       transition_progress=0.0, check_for_nan=False):
        """
        Grabs the command output from a preset with the index given by first.
        If a second preset index is given, render_preset will use a Transition class to generate the output
        according to transition_progress (0.0 = 100% first, 1.0 = 100% second)
        """
        first_buffer = first_preset.draw_to_buffer(first_buffer)
        if check_for_nan:
            for item in first_buffer.flat:
                if math.isnan(item):
                    raise ValueError

        if second_preset is not None:
            second_buffer = second_preset.draw_to_buffer(second_buffer)
            if check_for_nan:
                for item in second_buffer.flat:
                    if math.isnan(item):
                        raise ValueError

            if in_transition and transition is not None:
                first_buffer = transition.get(first_buffer, second_buffer,
                                              transition_progress)
                if check_for_nan:
                    for item in first_buffer.flat:
                        if math.isnan(item):
                            raise ValueError

        return first_buffer
