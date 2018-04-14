# Expelliarmus

## Requirements
* Python 2.7
* Python module networkx
* libguestfs-tools (>= 1.36.x)
* python-guestfs

### Use with Ubuntu
* ```sudo apt-get install python2.7 python-pip```
* ```sudo pip install networkx```
* ```sudo apt-get install libguestfs-tools```
* ```sudo apt-get install python-guestfs```

Over the standard repositories, libguestfs is currently only available in 1.32.2.
For some tools this creates problems together with Ubuntu, which is why we require libguestfs as a manual build as well:
* download and build according to http://libguestfs.org/guestfs-building.1.html
* the file ```run.sh``` should be present after correct build
