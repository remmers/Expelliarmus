FROM remmers/ubuntubase-gui

# Do not run container as root
# for now: same UID/GID as current user (otherwise no gui because of xhost)
RUN	export uid=1001 gid=1001 && \
	groupadd --system --gid ${gid} developer && \
	useradd  --system --gid ${gid} --groups audio,video --uid ${uid} developer && \
	mkdir -p /home/developer && \
	chown -R ${uid}:${gid} /home/developer

COPY Docker/tempRepository /var/tempRepository
RUN	echo "deb file:///var/tempRepository ./" >> /etc/apt/sources.list.d/tempRepo.list && \
	DEBIAN_FRONTEND=noninteractive apt-get update -qq -o Dir::Etc::sourcelist="/etc/apt/sources.list.d/tempRepo.list" && \
	DEBIAN_FRONTEND=noninteractive apt-get install cassandra -qqy --allow-unauthenticated && \
	rm /etc/apt/sources.list.d/tempRepo.list && \
	DEBIAN_FRONTEND=noninteractive apt-get autoremove -qqy && \
	DEBIAN_FRONTEND=noninteractive apt-get clean -qqy && \
	rm -rf /var/lib/apt/lists/*
CMD /usr/bin/cassandra