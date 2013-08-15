# Outputs a JSON scene file, either for simulation or for reading 
# pixel locations from a file or device.

import random

def random_location(x_lower = 0, x_upper = 100, y_lower = 0, y_upper = 100):
    """ Returns a bounded, random Location.
    """
    x = random.randint(x_lower, x_upper - 1)
    y = random.randint(y_lower, y_upper - 1)
    return (x, y)

def make_locations():
    x_width = 6*6
    y_width = 18
    count = 250
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

def read_locations():
    locations = set()
    f = open("/Users/mookerji/Dropbox/projects/burningman_project/clone-firemix/firemix/diodberg/foo", 'r')
    for line in f:
        words = line.split()
        x, y = (int(words[0]), int(words[1]))
        locations.add((x,y))
    f.close()
    return locations

def main():
    locations = make_locations()
    i, j = 0, 0
    count = 0
    xc, yc = 17.5, 630
    run = 17.25
    ans = """ {
    \t"backdrop_enable": true, 
    \t"backdrop_filename": "grid.png", 
    \t"center": [320, 320], 
    \t"extents": [640, 640],
    \t"file-type": "scene", 
    \t"fixtures": [\n"""
    for loc in locations:
        x, y = loc
        xp, yp = xc + x*run, yc - y*run
        strand = 0 if count < 125 else 1
        # TODO: Remove if using second half.
        # strand = 0 if y < 18 else 1
        address = i if strand is 0 else j
        ans += """ \n\t\t\t{
        \t\t\t"address": %d, 
        \t\t\t"pixels": 1, 
        \t\t\t"pos1": [%d, %d], 
        \t\t\t"pos2": [%d, %d], 
        \t\t\t"loc": [%d, %d], 
        \t\t\t"strand": %d, 
        \t\t\t"type": "linear"
        \t\t},""" % (address, xp, yp, xp, yp, x, y, strand)
        if strand is 0:
            i += 1
        else: 
            j += 1
        count += 1
    ans = ans.rstrip(",")
    ans += "\n\t],\t"
    ans += """\n\t"labels_enable": false, 
    \t"locked": true, 
    \t"name": "Sim", 
    \t"strand-settings": [
    \t\t{
    \t\t\t"color-mode": "RGB8", 
    \t\t\t"enabled": true, 
    \t\t\t"id": 0
    \t\t},
    \t\t{
    \t\t\t"color-mode": "RGB8", 
    \t\t\t"enabled": true, 
    \t\t\t"id": 1
    \t\t}
    \t]\n}"""
    print ans 

if __name__ == '__main__':
    main()
