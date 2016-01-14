FROM sxmichael/python-docker
MAINTAINER Oded Lazar <odedlaz@gmail.com>

RUN pip install newrelic-plugin-agent
COPY newrelic-plugin-agent.sh /etc/newrelic/
COPY config/newrelic-plugin-agent.cfg config/make.py /etc/newrelic/config/

WORKDIR "/etc/newrelic"
CMD ["/bin/bash", "newrelic-plugin-agent.sh"]

VOLUME ["/etc/newrelic/backends"]
