from lib.buffer_utils import BufferUtils
from lib.raw_preset import RawPreset
from lib.parameters import FloatParameter, HLSParameter, StringParameter

class CombinePresets(RawPreset):
    """
    Preset that loads two presets and renders both
    Combine requires a transition that will render an arbitrary progress point
    """

    def setup(self):
        self.add_parameter(StringParameter('first-preset', ""))
        self.add_parameter(StringParameter('second-preset', ""))
        self.add_parameter(FloatParameter('transition-progress', 0.5))
        self.add_parameter(StringParameter('transition-mode', "Additive Blend"))
        self.add_parameter(StringParameter('layer', 'default'))
        self.parameter_changed(None)
        self._preset1_buffer = BufferUtils.create_buffer()
        self._preset2_buffer = BufferUtils.create_buffer()

    def layer(self):
        return self._mixer.layer_by_name(self.parameter('layer').get())

    def parameter_changed(self, parameter):
        layer = self.layer()
        if layer is None:
            return

        self._transition = layer.get_transition_by_name(self.parameter('transition-mode').get())
        if self._transition:
            self._transition.reset()

    def reset(self):
        self.parameter_changed(None)

    def draw(self, dt):
        layer = self.layer()
        if layer is None:
            return

        preset1 = layer._playlist.get_preset_by_name(self.parameter('first-preset').get())
        preset2 = layer._playlist.get_preset_by_name(self.parameter('second-preset').get())

        if preset1 and preset2 and self._transition:
            # this is here because many transitions are set up to only play from start to end :(
            # Combine renders arbitrary transition frames
            self._transition.reset()

            preset1.tick(dt)
            preset2.tick(dt)

            preset1_buffer = preset1.draw_to_buffer(self._preset1_buffer)
            preset2_buffer = preset2.draw_to_buffer(self._preset2_buffer)

            self._pixel_buffer = self._transition.get(
                preset1_buffer, preset2_buffer,
                self.parameter('transition-progress').get())
