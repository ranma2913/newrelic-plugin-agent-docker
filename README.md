## newrelic-plugin-agent-docker

This repository contains **Dockerfile** of [newrelic-plugin-agent](https://github.com/MeetMe/newrelic-plugin-agent/) for [Docker](https://www.docker.com/)'s [automated build](https://hub.docker.com/r/gici/newrelic-plugin-agent-docker/) published to the public [Docker Hub Registry](https://registry.hub.docker.com/).

It will monitor instances of services supported by [newrelic-plugin-agent](https://github.com/MeetMe/newrelic-plugin-agent/)
that were configured by the user or will try to automatically monitor supported instances running inside docker containers on the same machine.

### Base Docker Image

* [gici/python](https://hub.docker.com/r/gici/python/)


### Installation

1. Install [Docker](https://www.docker.com/).

2. Download [automated build](https://hub.docker.com/r/gici/newrelic-plugin-agent-docker/) from public [Docker Hub Registry](https://registry.hub.docker.com/): `docker pull gici/newrelic-plugin-agent-docker`

   (alternatively, you can build an image from Dockerfile: `docker build -t="gici/newrelic-plugin-agent-docker" github.com/devsenexx/newrelic-plugin-agent-docker`)

### Usage
```sh
docker run -d --net=host -v /var/run/docker.sock:/var/run/docker.sock:ro -e NEWRELIC_KEY="YOUR_KEY" gici/newrelic-plugin-agent-docker
```

#### Attach custom backend configuration

  1. Create a mountable data directory `<data-dir>` on the host.

  2. Create a backend configuration file at `<backends-dir>/<backend_name>.yml`.
     for example, create an elasticsearch configuration file at ```<backends-dir>/elasticsearch.yml```:

```yml
name: my-elasticsearch-cluster
host: localhost
port: 9200
scheme: http
```

  3. Start a container by mounting data directory and specifying the custom configuration file:

```sh
docker run -d --net=host -v /var/run/docker.sock:/var/run/docker.sock:ro -v <backends-dir>/backends:/etc/newrelic/backends -e NEWRELIC_KEY="YOUR_KEY" gici/newrelic-plugin-agent-docker
```
