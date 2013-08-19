import collections

class AudioEmitter(object):
    """An AudioEmitter represents a source of sound in the scene.

    Every AudioEmitter is uniquely identified by a group which is just a unique
    id. When using Mixxx, the group can be used to identify the type of the
    source. For example, '[Sampler1]' identifies the emitter as the 1st sample
    deck in Mixxx.

    Features about audio streams that are extracted by external programs
    (e.g. Mixxx) and reported to FireMix via OSC are stored in this class.

    First-class features include:

    - position : A 3D (x, y, z) vector locating the AudioEmitter in space.

    - beat : A boolean that represents whether a beat is currently active.

    - onset : A boolean that represents whether an onset is currently active. An
      onset is roughly defined as a peak in the audio stream caused by an
      instrument, vocal, or beat.

    - vumeter : A real value that represents the log-scale amplitude of the
      audio signal. Note that Mixxx reports the VU meter by averaging over ~33ms
      intervals.

    - silence : A boolean that represents whether the emitter is currently
      silent. Mixxx's default silence threshold is -60dB.

    - bpm : A real value that represents the average BPM of the audio stream (if
      available).

    - pitch: The current instantaneous average pitch of the audio stream.

    """

    def __init__(self, group):
        self._group = group
        self._features = collections.defaultdict(lambda: {})
        self._target_position = (0, 0, 0)

    def group(self):
        return self.group

    def on_feature_update(self, feature_name, feature_dict):
        self._features[feature_name].update(feature_dict)

    def feature_value(self, feature_name):
        """Returns the latest value of the feature or None if no value is
        available."""
        return self._features[feature_name].get('value', None)

    def set_target_position(self, pos):
        self._target_position = pos

    def target_position(self):
        return self._target_position

    def position(self):
        """Convenience function for getting the position of the AudioEmitter in
        space. Returns None if the position is not available, otherwise
        (x, y, z)."""

        x = self.feature_value('pos_x')
        if x is None:
            return None

        y = self.feature_value('pos_y')
        if y is None:
            return None

        z = self.feature_value('pos_z')
        if z is None:
            return None

        return (x, y, z)
