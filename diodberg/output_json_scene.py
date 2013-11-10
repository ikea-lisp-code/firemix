# Generates json files for testing and configuring the wall.

import json
import random
import sys

from lib.fixture import Fixture
from lib.route import Route


# Maps for finding the total horizontal displacement across a set of panels
# configured into a climbing wall.
# panel number -> number of (horizontal, vertical) hold spaces.
# Configuration from Burning Man 2013.
bm_panel_dimensions = {0: (6, 18),
                       1: (6, 18),
                       2: (10, 18),
                       3: (6, 18),
                       4: (6, 18),
                       5: (10, 18),
                       6: (11, 18),
                       7: (6, 18)}

langton_panel_dimensions = {0: (6, 18),
                            1: (6, 18),
                            2: (6, 18),
                            3: (6, 18),
                            4: (6, 18)}

def random_location(x_lower = 0, x_upper = 100, y_lower = 0, y_upper = 100):
    """ Returns a bounded, random Location.
    """
    x = random.randint(x_lower, x_upper - 1)
    y = random.randint(y_lower, y_upper - 1)
    return (x, y)

def make_locations(x_width, y_height, count, x_offset):
    """ Generates random locations in a range, split artificially across
    the grid geometry.
    """
    bottom = set()
    while len(bottom) < count:
        loc = random_location(x_offset, x_offset + x_width, 0, y_height)
        bottom.add(loc)
    return bottom


def map_loc_to_pixel((x, y), xc = 17.25, yc = 630, run = 17.25):
    """Takes a grid location and returns a pixel location. Parameters here are
    chosen for the grid size in grid.png.
    """
    xp, yp = xc + x*run, yc - y*run
    return (xp, yp)


def map_grid_loc_to_pixel((grid, x, y), panel_dimensions = bm_panel_dimensions, xc = 17.25, yc = 630, run = 17.25):
    """Maps a (grid number, x, y) and returns a pixel location. Parameters here
    are choen for the grid size in grid.png.
    """
    x_offset = 0
    for panel_index, panel_dim in panel_dimensions.iteritems():
        if panel_index < grid:
            width, height = panel_dim
            x_offset += width*xc
    xp, yp = xc + x*run + x_offset, yc - y*run
    return (xp, yp)


def parse_fixture_line(line):
    """ Parses hold specifications.
    Line format is <universe> <address> <panel number> <x> <y> [<route number>]
    """
    len_minus_routes = 5
    words = line.split()
    if len(words) > 0 and words[0] == "#":
        return None
    assert len(words) >= len_minus_routes
    strand, address = int(words[0]), int(words[1])
    panel_number = int(words[2])
    x, y = (int(words[3]), int(words[4]))
    routes = set(map(int, words[len_minus_routes:]))
    parsed = {"strand": strand,
              "address": address,
              "panel_number": panel_number,
              "grid_loc": (x, y),
              "routes": list(routes)}
    return parsed


def simulate_fixtures(x_width = 36, y_height = 18, total = 250, x_offset = 0):
    """ Generate a set of fixtures for a scene. DMX universe is split in-half
    by default.
    """
    locations = make_locations(x_width, y_height, total, x_offset)
    fixtures = []
    i, j = 0, 0
    count = 0
    for grid_loc in locations:
        strand = int(count >= total/2)
        address = j if strand else i
        pixels = 1
        data = {"strand": strand,
                "address": address,
                "pixels": pixels,
                "pos1": map_loc_to_pixel(grid_loc),
                "pos2": map_loc_to_pixel(grid_loc),
                "grid_loc": grid_loc}
        fixtures.append(Fixture(data))
        if not strand:
            i += 1
        else:
            j += 1
        count += 1
    return fixtures


def read_fixtures(filename):
    """Reads scene pixel locations from a file. See definition for
    parse_fixture_line definition for the file format here.
    """
    fixtures = []
    f = open(filename, 'r')
    routes = {}
    for line in f:
        parsed = parse_fixture_line(line)
        if parsed is None:
            continue
        strand = parsed["strand"]
        address = parsed["address"]
        panel_number = parsed["panel_number"]
        x, y = parsed["grid_loc"]
        pos1 = map_grid_loc_to_pixel((panel_number, x, y),
                                     panel_dimensions = langton_panel_dimensions)
        pixels = 1
        route_indices = parsed["routes"]
        data = {"strand": strand,
                "address": address,
                "pixels": pixels,
                "pos1": pos1,
                "pos2": pos1,
                "grid_loc": (x, y)}
        fixtures.append(Fixture(data))
        for route_index in route_indices:
            if route_index in routes:
                routes[route_index].fixtures.append(data)
            else:
                routes[route_index] = Route({"active": False,
                                             "color": (1, 0, 0),
                                             "fixtures": [data],
                                             "index": route_index})
    f.close()
    return routes, fixtures


def build_scene_from_fixtures(fixtures, scene_name, num_strands = 1):
    """ Builds a scene file from fixtures.
    """
    scene = dict()
    scene["backdrop_enable"] = True
    scene["backdrop_filename"] = "grid.png"
    scene["center"] = (320, 320)
    scene["extents"] = (640, 640)
    scene["file-type"] = "scene"
    scene["fixtures"] = fixtures
    scene["labels_enable"] = False
    scene["locked"] = True
    scene["name"] = scene_name
    s = lambda strand: {"color-mode": "RGB8", "enabled": True, "id" : strand}
    scene["strand-settings"] = [s(i) for i in xrange(num_strands)]
    return scene


def build_routes_file(routes, name):
    """ Builds the routes file from ... the routes.
    """
    top = dict()
    top["file-type"] = "routes"
    top["name"] = name
    top["routes"] = routes
    return top


def encode_json(obj):
    if isinstance(obj, Fixture):
        schema = {"strand": obj.strand,
                  "address": obj.address,
                  "pixels": obj.pixels,
                  "pos1": obj.pos1,
                  "pos2": obj.pos2,
                  "grid_loc": obj.grid_loc}
        return schema
    if isinstance(obj, Route):
        schema = {"active": obj.active,
                  "color": obj.color,
                  "fixtures": obj.fixtures,
                  "index": obj.index}
        return schema
    raise TypeError(repr(obj) + ' is not JSON serializable')


def write_to_json(data, name):
    """ Dumps data to local directory.
    """
    f = open(name + ".json", 'w')
    json.dump(data, f, indent = 4, sort_keys = True, default = encode_json)
    f.close()


def read(scene_name):
    """Reads a human-written file specifying a scene and climbing routes.
    """
    routes, fixtures = read_fixtures(scene_name)
    scene = build_scene_from_fixtures(fixtures, scene_name)
    write_to_json(scene, scene_name)
    if routes:
        write_to_json(build_routes_file(routes, scene_name), scene_name + "-routes")


def simulate(scene_name):
    """Builds a simulation panel and a simulation set of climbing routes.
    """
    fixtures = simulate_fixtures()
    scene = build_scene_from_fixtures(fixtures, scene_name)
    write_to_json(scene, scene_name)


if __name__ == '__main__':
    if len(sys.argv) == 3 and (sys.argv[1] == "read"):
        read(sys.argv[2])
    elif len(sys.argv) == 3 and (sys.argv[1] == "simulate"):
        simulate(sys.argv[2])
    else:
        print "Incorrect usage: "
        print "python output_json_scene.py simulate <scene name>"
        print "python output_json_scene.py read <scene name>"
