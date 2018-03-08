FROM ubuntu:latest
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
	DEBIAN_FRONTEND=noninteractive apt-get install x11-apps libcanberra-gtk3-module dbus dbus-x11 sudo -qqy --no-install-recommends  && \
	dbus-uuidgen > /var/lib/dbus/machine-id
