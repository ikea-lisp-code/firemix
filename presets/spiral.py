import numpy as np
import colorsys
import random
import math

from lib.raw_preset import RawPreset
from lib.parameters import FloatParameter, HLSParameter
from lib.color_fade import ColorFade
from lib.colors import clip

class SpiralGradient(RawPreset):
    """Spiral gradient that responds to onsets"""
       
    _fader = None
    _fader_steps = 256
    
    def setup(self):
        self.add_parameter(FloatParameter('speed', 0.3))
        self.add_parameter(FloatParameter('hue-speed', 0.3))
        self.add_parameter(FloatParameter('angle-hue-width', 2.0))
        self.add_parameter(FloatParameter('radius-hue-width', 1.5))        
        self.add_parameter(FloatParameter('wave-hue-width', 0.1))        
        self.add_parameter(FloatParameter('wave-hue-period', 0.1))        
        self.add_parameter(FloatParameter('wave-speed', 0.1))        
        self.add_parameter(FloatParameter('hue-step', 0.1))    
        self.add_parameter(HLSParameter('color-start', (0.0, 0.5, 1.0)))
        self.add_parameter(HLSParameter('color-end', (1.0, 0.5, 1.0)))
        self.hue_inner = 0
        self.color_offset = 0
        self.wave_offset = random.random()

        self.pixels = self.scene().get_all_pixels_logical()
        cx, cy = self.scene().center_point()

        """
        self.locations = np.zeros((cls._num_strands, self.scene().fixtures() * cls._max_pixels, 3), dtype=np.float32)
        for f in self.scene().fixtures():
            f_locations = np.array([])
            for p in range(f.pixels):
                f_locations.concatenate(self.scene().get_pixel_location((f.strand, f.address, p)))
            self.locations.concatenate(f_locations)
        """

        self.locations = np.asarray(zip(*self.scene().get_all_pixel_locations())[1])
        x,y = self.locations.T
        x -= cx
        y -= cy
        self.pixel_distances = np.sqrt(np.square(x) + np.square(y))
        self.pixel_angles = np.arctan2(y, x) / (2.0 * math.pi)
        self.pixel_distances /= max(self.pixel_distances)

        self.parameter_changed(None)

    def parameter_changed(self, parameter):
        fade_colors = [self.parameter('color-start').get(), self.parameter('color-end').get(), self.parameter('color-start').get()]

        self._fader = ColorFade(fade_colors, self._fader_steps)

    def reset(self):
        pass

    def draw(self, dt):
        if self._mixer.is_onset():
            self.hue_inner = self.hue_inner + self.parameter('hue-step').get()

        self.hue_inner += dt * self.parameter('hue-speed').get()
        self.wave_offset += dt * self.parameter('wave-speed').get()
        self.color_offset += dt * self.parameter('speed').get()

        wave_hue_period = 2 * math.pi * self.parameter('wave-hue-period').get()
        wave_hue_width = self.parameter('wave-hue-width').get()
        radius_hue_width = self.parameter('radius-hue-width').get()
        angle_hue_width = self.parameter('angle-hue-width').get()

        angles = np.mod(1.0 + self.pixel_angles + np.sin(self.wave_offset + self.pixel_distances * wave_hue_period) * wave_hue_width, 1.0)
        hues = self.color_offset + (radius_hue_width * self.pixel_distances) + (2 * np.abs(angles - 0.5) * angle_hue_width)
        hues = np.mod(hues, 1.0) * self._fader_steps
        colors = map(self._fader.get_color, hues)

        """
        # Do we prefer numpy function math? So far seems to be harder to read with no benefit.
        angles = np.mod(np.add(np.sin(np.add(np.multiply(self.pixel_distances, wave_hue_period),self.wave_offset)) * wave_hue_width, self.pixel_angles), 1.0)
        stuff = np.add(np.multiply(np.abs(np.subtract(angles, 0.5)), 2 * angle_hue_width), self.color_offset)
        hues = np.add(np.multiply(self.pixel_distances, radius_hue_width), stuff)
        hues = np.multiply(np.mod(hues, 1.0), self._fader_steps)
        colors = map(self._fader.get_color, hues)
        """

        for i in range(len(self.pixels)):
            color = colors[i]
            self.setPixelHLS(self.pixels[i], ((color[0] + self.hue_inner) % 1.0, color[1], color[2]))
