This directory contains Raspberry Pi-specific modules for receiving UDP packets
and writing them over DMX-512 via USB/serial. Some additional notes:

* `sudo python serial_utils.py' runs a script to probe all the holds on a wall.

* data/settings.json lists a client publishing to the Pi on the 1611 local
  network, to continuously read the UDP on the Pi, run `sudo python
  daemon.py&'.

* Running Qt applications on the Pi requires X11 authorization, even if you're
  not using X11. You might get an error claiming that "X11 connection rejected
  because of wrong authentication.". If you do, and you likely will if you just
  booted the Pi, run:

         sudo touch /root/.Xauthority
         xauth list

  You'll see output with this (with a different hash on the end):

         raspberrypi/unix:10 MIT-MAGIC-COOKIE-1 16c744e48d9f1bcede74e25b5f83b526

  Copy that and then run:

         sudo xauth add raspberrypi/unix:10 MIT-MAGIC-COOKIE-1 16c744e48d9f1bcede74e25b5f83b526

  where you've replaced the second half of that command with the output of
  xauth list. This will likely be automated at startup at some point.

* This fork of firemix requires some additional dependencies. Specifically: The
  liblo OSC implementation and it's python bindings. "./configure && make &&
  sudo make install" work for development version at
  http://downloads.sourceforge.net/liblo/liblo-0.26.tar.gz , followed by "sudo
  pip install pyliblo". Also profilehoooks: "sudo pip installprofilehooks".

* To run firemix with a routes, the following command line should work:

         python firemix.py test_september_2013.txt --playlist default1 --route_layer test_september_2013.txt-routes --route_playlist default2

  provided that you have the test_september_2013.txt.json in data/scenes/ and
  test_september_2013.txt-routes.json in data/routes/. The default (RGB) color
  for a route is red.
