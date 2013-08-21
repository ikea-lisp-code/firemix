from lib.buffer_utils import BufferUtils
from lib.fixture import Fixture


class Route(object):
    """ Climbing route specification, basically a group of fixtures with 
    dictionary access by Fixture.pos1.
    """ 
        
    __pixel_offset = 0

    def __init__(self, data = {}):
        self._data = data
        self.active = data.get("active", False)
        self.color = tuple(data.get("color", (0, 0, 0)))
        self.fixtures = [Fixture(item) for item in data.get("fixtures")]
        self.index = data.get("index", 0)
        # Caches
        self._addresses = []
        self._indices = []
            
    @property 
    def addresses(self):
        """ Returns logical addresses of fixtures.
        """
        if not self._addresses : 
            f = lambda fd: (fd.strand, fd.address, Route.__pixel_offset)
            self._addresses = [f(fixture) for fixture in self.fixtures]
        return self._addresses

    @property
    def indices(self):
        """ Returns indices into pixel buffer.
        """ 
        if not self._indices:
            self._indices = map(BufferUtils.logical_to_index, self.addresses)
        return self._indices

    def __len__(self):
        return len(self.fixtures)
        
    def __repr__(self):
        out = [self.active, self.color, self.fixtures, self.index]
        return "<Route(active=%s,color=%s,fixtures=%s,index=%s)>" % tuple(map(str, out))
