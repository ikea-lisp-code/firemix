import ast
import os

from lib.color_fade import ColorFade
from lib.json_dict import JSONDict
from lib.parameters import StringParameter
from lib.parameters import IntParameter
from lib.raw_preset import RawPreset
from lib.route import Route


class RouteManager(RawPreset):
    """RouteManager keeps track of active climbing routes on the wall, rendering
    them as a separate layer from the background.
    """

    def __init__(self, mixer, name):
        RawPreset.__init__(self, mixer, name)
        route_fd = mixer._app.args.route_layer
        self._filepath = os.path.join(os.getcwd(), "data", "routes", "".join([route_fd, ".json"]))
        self._data = JSONDict("routes", self._filepath, False)
        self._route_dict = {}
        for index, route_spec in self._data["routes"].iteritems():
            route = Route(route_spec)
            self._route_dict[route.index] = route

    def setup(self):
        # initial colors
        self.add_parameter(StringParameter('init-colors', "{1: (0,0.5,1), 2: (1,0.5,1)}"))
        init_colors = ast.literal_eval(self.parameter('init-colors').get())
        assert len(init_colors) == len(self._route_dict)
        # final colors
        self.add_parameter(StringParameter('final-colors', "{1: (1,0.5,1), 2: (0,0.5,1)}"))
        final_colors = ast.literal_eval(self.parameter('final-colors').get())
        assert len(final_colors) == len(self._route_dict)
        # steps
        # final colors
        self.add_parameter(IntParameter('steps', 256))
        # speeds
        self.add_parameter(StringParameter('speeds', "{1: 0.01, 2: 0.02"))
        speeds = ast.literal_eval(self.parameter('speeds').get())
        assert len(speeds) == len(self._route_dict)
        # fill faders
        for index, fader in self._route_dict.iteritems():
            initial_color = init_colors[index]
            final_color = final_colors[index]
            steps = self.parameter('steps').get()
            self._route_dict[index].color = initial_color
            self._route_dict[index].fader = ColorFade((initial_color, final_color), steps)
            self._route_dict[index].speed = speeds[index]

    def reset(self):
        pass

    def parameter_changed(self, parameter):
        pass

    def can_transition(self):
        return False

    def draw(self, dt):
        for index, route in self._route_dict.iteritems():
            if route.active:
                f = lambda i: self.setPixelHLS(i, route.color)
                map(f, route.indices)
                route.update(dt)

    def on_feature(self, feature):
        pass
