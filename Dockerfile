FROM sxmichael/python-docker
MAINTAINER Oded Lazar <odedlaz@gmail.com>
RUN apt-get update && apt-get install -y libpq-dev
RUN pip install psycopg2 newrelic-plugin-agent docker-py fuzzywuzzy python-Levenshtein
COPY newrelic-plugin-agent.sh /etc/newrelic/
COPY config/newrelic-plugin-agent.cfg config/make.py /etc/newrelic/config/

ADD defaults /etc/newrelic/defaults/

WORKDIR "/etc/newrelic"
CMD ["/bin/bash", "newrelic-plugin-agent.sh"]

VOLUME ["/etc/newrelic/backends"]