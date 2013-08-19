import math
import numpy as np
from collections import defaultdict

from lib.raw_preset import RawPreset
from lib.parameters import StringParameter, FloatParameter, HLSParameter, IntParameter
from lib.color_fade import ColorFade

class PositionPulser(RawPreset):
    class AudioEmitterPulser(object):
        def __init__(self, audio_emitter, fade_colors, fade_steps):
            self.audio_emitter = audio_emitter
            self._fader = ColorFade(fade_colors, fade_steps)
            self.value = 0.0
            self.color = 0

    def setup(self):
        self.audio_emitter_pulsers = {}
        self.add_parameter(StringParameter('feature', 'vumeter'))
        self.feature = self.parameter('feature').get()
        self.add_parameter(FloatParameter('scale', 10.0))
        self.add_parameter(HLSParameter('color-start', (0.0, 0.5, 1.0)))
        self.add_parameter(HLSParameter('color-end', (1.0, 0.5, 1.0)))
        self.add_parameter(IntParameter('color-steps', 256))
        self.add_parameter(FloatParameter('color-speed', 10.0))

    def parameter_changed(self, parameter):
        self.feature = self.parameter('feature').get()

    def reset(self):
        self.pixel_locations = self.scene().get_all_pixel_locations()

    def draw(self, dt):
        x, y = self.pixel_locations.T

        # Make a blank color canvas for additive mixing.
        hues = np.zeros(x.shape, float)

        # Make every pixel dark.
        luminances = np.zeros(x.shape, float)

        scale = self.parameter('scale').get()
        color_speed = self.parameter('color-speed').get()
        for _, pulser in self.audio_emitter_pulsers.iteritems():
            position = pulser.audio_emitter.position()

            if not position:
                continue

            pulser_x, pulser_y, _ = position

            # For every pixel, get the vector between the pixel and this pulser.
            dx, dy = (self.pixel_locations - (pulser_x, pulser_y)).T

            # And make a column vector of the distances between every pixel and
            # this pulser.
            pixel_distances = np.sqrt(np.square(dx) + np.square(dy))

            # Select all pixels less than scale * feature-value from the pulser.
            selector = pixel_distances < pulser.value * scale

            # Color them with a color from the fader. Add the color so that
            # overlapping colors mix.
            hues[selector] += pulser._fader.get_color_wrapped(pulser.color)[0]

            # and illuminate them.
            luminances[selector] = 0.5

            # Increment the pulser's color ticker by the color-speed parameter.
            pulser.color += color_speed * dt

        self.setAllHLS(hues, luminances, 1)

    def on_feature(self, feature):
        if feature['feature'] != self.feature:
            return

        group = feature['group']
        audio_emitter = self._mixer.audio_emitter(group)

        pulser = self.audio_emitter_pulsers.get(group, None)
        if pulser is None:
            fade_colors = [self.parameter('color-start').get(),
                           self.parameter('color-end').get(),
                           self.parameter('color-start').get()]
            color_steps = self.parameter('color-steps').get()
            pulser = PositionPulser.AudioEmitterPulser(
                audio_emitter, fade_colors, color_steps)
            self.audio_emitter_pulsers[group] = pulser
        pulser.value = feature['value']

class PositionDonutParticles(RawPreset):
    """Emits 'donut' particles from positions of AudioEmitters when the
    specified feature parameter goes high."""

    class DonutParticle(object):
        def __init__(self, position, fade_colors, fade_steps):
            self.position = position
            self.distance = 0
            self.color = 0
            self._fader = ColorFade(fade_colors, fade_steps)
            self.alive = True

    def setup(self):
        self.particles = []
        self.max_distance = 0
        self.feature_value_triggered = defaultdict(lambda: False)
        self.add_parameter(StringParameter('feature', 'beat'))
        self.add_parameter(FloatParameter('speed', 100))
        self.add_parameter(FloatParameter('width', 5))
        self.add_parameter(HLSParameter('color-start', (0.0, 0.5, 1.0)))
        self.add_parameter(HLSParameter('color-end', (1.0, 0.5, 1.0)))
        self.add_parameter(IntParameter('color-steps', 256))
        self.add_parameter(FloatParameter('color-speed', 10.0))

    def parameter_changed(self, parameter):
        self.feature = self.parameter('feature').get()

    def reset(self):
        self.pixel_locations = self.scene().get_all_pixel_locations()
        extent_x, extent_y = self.scene().extents()
        self.max_distance = math.sqrt(extent_x ** 2 + extent_y ** 2)

    def draw(self, dt):
        x, y = self.pixel_locations.T

        hues = np.zeros(x.shape, float)
        luminances = np.zeros(x.shape, float)

        speed = self.parameter('speed').get()
        width = self.parameter('width').get()
        color_speed = self.parameter('color-speed').get()
        for particle in self.particles:
            particle_x, particle_y, _ = particle.position
            particle.distance += dt * speed

            # For every pixel, get the vector between the pixel and this particle.
            dx, dy = (self.pixel_locations - (particle_x, particle_y)).T

            # And make a column vector of the distances between every pixel and
            # this particle.
            pixel_distances = np.sqrt(np.square(dx) + np.square(dy))

            # Select all pixels less than width distance from current location
            # of the particle's width.
            selector = np.abs(pixel_distances - particle.distance) < width

            # Color them with a color from the fader. Add the color so that
            # overlapping colors mix.
            hues[selector] += particle._fader.get_color_wrapped(particle.color)[0]

            # and illuminate them.
            luminances[selector] = 0.5

            # Increment the pulser's color ticker by the color-speed parameter.
            particle.color += color_speed * dt

            if particle.distance > self.max_distance:
                particle.alive = False

        self.particles = filter(lambda particle: particle.alive, self.particles)

        self.setAllHLS(hues, luminances, 1)

    def on_feature(self, feature):
        if feature['feature'] != self.feature:
            return

        feature_value = feature['value']

        group = feature['group']
        audio_emitter = self._mixer.audio_emitter(group)

        if not feature_value:
            self.feature_value_triggered[group] = False
            return

        # We already processed this feature.
        if self.feature_value_triggered[group]:
            return

        position = audio_emitter.position()
        if position is None:
            return

        fade_colors = [self.parameter('color-start').get(),
                       self.parameter('color-end').get(),
                       self.parameter('color-start').get()]
        color_steps = self.parameter('color-steps').get()

        self.particles.append(PositionDonutParticles.DonutParticle(
            position, fade_colors, color_steps))
        self.feature_value_triggered[group] = True
