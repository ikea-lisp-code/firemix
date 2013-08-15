# Outputs a JSON scene file, either for simulation or for reading 
# pixel locations from a file or device.
# Example:
# python output_json_scene.py Sim | pbcopy 

import json
import random
import sys



def random_location(x_lower = 0, x_upper = 100, y_lower = 0, y_upper = 100):
    """ Returns a bounded, random Location.
    """
    x = random.randint(x_lower, x_upper - 1)
    y = random.randint(y_lower, y_upper - 1)
    return (x, y)

def make_locations(x_width = 36, y_width = 18, count = 250):
    bottom = set()
    top = set()
    while len(bottom) < count:
        loc = random_location(0, x_width, 0, y_width)
        bottom.add(loc)
    # TODO: Remove if using second half 
    # while len(top) is not count/2:
    #     top.add(random_location(0, x_width, y_width + 1, y_width*2+1))
    locations = set()
    locations.update(top)
    locations.update(bottom)
    return locations

def read_locations(filename):
    locations = set()
    f = open(filename, 'r')
    for line in f:
        words = line.split()
        x, y = (int(words[0]), int(words[1]))
        locations.add((x,y))
    f.close()
    return locations

def main(scene_name, filename):
    locations = read_locations(filename) if filename else make_locations()
    i, j = 0, 0
    count = 0
    xc, yc = 17.5, 630
    run = 17.25
    scene = dict()
    scene["backdrop_enable"] = True
    scene["backdrop_filename"] = "grid.png"
    scene["center"] = (320, 320)
    scene["extents"] = (640, 640)
    scene["file-type"] = "scene"
    fixtures = []
    for loc in locations:
        x, y = loc
        xp, yp = xc + x*run, yc - y*run
        strand = 0 if count < 125 else 1
        # TODO: Remove if using second half.
        # strand = 0 if y < 18 else 1
        address = i if strand is 0 else j
        fixture = dict()
        fixture["address"] = address
        fixture["pixels"] = 1
        fixture["pos1"] = (xp, yp)
        fixture["pos2"] = fixture["pos1"]
        fixture["loc"] = loc
        fixture["strand"] = strand
        fixture["type"] = "linear"
        if strand is 0:
            i += 1
        else: 
            j += 1
        count += 1
        fixtures.append(fixture)
    scene["fixtures"] = fixtures
    scene["labels_enable"] = False
    scene["locked"] = True
    scene["name"] = scene_name
    s1 = {"color-mode": "RGB8",
          "enabled": True,
          "id" : 0
      }
    s2 = {"color-mode": "RGB8",
          "enabled": True,
          "id" : 1
      }
    scene["strand-settings"] = [s1, s2]
    print json.dumps(scene, indent = 4, sort_keys = True)

if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1], "")
    elif len(sys.argv) > 2:
        main(sys.argv[1], sys.argv[2])
    else: 
        print "python output_json_scene.py <scene name> <if reading, filename>"
