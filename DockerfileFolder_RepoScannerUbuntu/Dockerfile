FROM ubuntu:16.04


COPY DockerfileFolder_RepoScannerUbuntu/scanpackages.sh /opt/scanpackages.sh
RUN	DEBIAN_FRONTEND=noninteractive apt-get update -qqy --no-install-recommends && \
	DEBIAN_FRONTEND=noninteractive apt-get install dpkg-dev -qqy --no-install-recommends

CMD /opt/scanpackages.sh