// Asymptote-generated background for the simulation. To generate the png file
// used by firelight, run "asy -V -f png grid".

import math;

size(640, 640);
real offset = 6.;

for (int i = 0; i < 6; i += 1) {
    picture p = shift(i*offset,0)*grid(6,18);
    add(p, filltype = FillDraw(0.1, 0.1, rgb(grey)));
}
for (int i = 0; i < 6; i += 1) {
    picture p = shift(i*offset,19)*grid(6,18);
    add(p, filltype = FillDraw(0.1, 0.1, rgb(grey)));
}
