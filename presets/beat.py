import math
import numpy as np

from lib.raw_preset import RawPreset
from lib.parameters import StringParameter, FloatParameter, HLSParameter
from lib.color_fade import ColorFade

class BeatPositionCircles(RawPreset):

    class BeatParticle(object):
        _fader_steps = 256
        def __init__(self, pos, fade_colors):
            self.pos = pos
            self.distance = 0
            self.color = 0
            self._fader = ColorFade(fade_colors, self._fader_steps)
            self.alive = True
            self.feature = 'beat'

    def setup(self):
        self.beats = []
        self.add_parameter(StringParameter('feature', 'beat'))
        self.add_parameter(FloatParameter('speed', 100))
        self.add_parameter(FloatParameter('width', 5))
        self.add_parameter(HLSParameter('color-start', (0.0, 0.5, 1.0)))
        self.add_parameter(HLSParameter('color-end', (1.0, 0.5, 1.0)))

    def parameter_changed(self, parameter):
        self.feature = self.parameter('feature').get()

    def reset(self):
        self.pixel_locations = self.scene().get_all_pixel_locations()

    def draw(self, dt):
        x, y = self.pixel_locations.T

        hues = np.zeros(x.shape, float)
        luminances = np.zeros(x.shape, float)

        speed = self.parameter('speed').get()
        width = self.parameter('width').get()
        for beat in self.beats:
            beat.distance += dt * speed
            dx, dy = (self.pixel_locations - (beat.pos[0], beat.pos[1])).T
            pixel_distances = np.sqrt(np.square(dx) + np.square(dy))

            selector = np.abs(pixel_distances - beat.distance) < width
            hues[selector] += beat._fader.get_color(beat.color)[0]
            luminances[selector] = 0.5
            beat.color += 1

            if beat.distance > 1000:
                beat.alive = False

        self.beats = filter(lambda beat: beat.alive, self.beats)

        #hues = y / 1000.0 * 1.3

        # if self.beat_hold > 0:
        #     self.beat_hold -= 1
        #     hues *= 10

        self.setAllHLS(hues, luminances, 1)

    def on_feature(self, feature):
        if feature['feature'] == self.feature:
            self.beat = feature['value']

            if not self.beat:
                return

            group = feature['group']
            features_by_group = self._mixer.features_by_group[group]
            x = features_by_group['pos_x'].get('value', None)
            y = features_by_group['pos_y'].get('value', None)
            z = features_by_group['pos_z'].get('value', None)

            if x is not None and y is not None and z is not None:
                fade_colors = [self.parameter('color-start').get(),
                               self.parameter('color-end').get(),
                               self.parameter('color-start').get()]
                self.beats.append(BeatPositionCircles.BeatParticle((x, y, z), fade_colors))
