import os

from lib.json_dict import JSONDict
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
        pass

    def reset(self):
        pass

    def parameter_changed(self, parameter):
        pass

    def can_transition(self):
        return False

    def draw(self, dt):
        for index, route in self._route_dict.iteritems():
            if route.active:
                f = lambda i: self.setPixelRGB(i, route.color)
                map(f, route.indices)

    def on_feature(self, feature):
        pass
