#!/bin/bash
cd /var/tempRepository && \
dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz