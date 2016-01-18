FROM gici/python
MAINTAINER Oded Lazar <odedlaz@gmail.com>

# supervisor
RUN apt-get update && apt-get install -y -qq supervisor && \
    mkdir -p /etc/supervisor/conf.d/ && \
    mkdir -p /var/log/supervisor/

ADD supervisord.conf /etc/supervisor/supervisord.conf

# supervisor-newrelic-plugin-agent
ADD supervisord-newrelic-plugin-agent.conf /etc/supervisor/conf.d/newrelic-plugin-agent.conf

# newrelic-plugin-agent
RUN apt-get update && apt-get install -y libpq-dev
RUN pip install psycopg2 newrelic-plugin-agent docker-py fuzzywuzzy python-Levenshtein

COPY newrelic-plugin-agent.sh /etc/newrelic/
COPY config/newrelic-plugin-agent.cfg config/make.py /etc/newrelic/config/

# add default configurations
ADD defaults /etc/newrelic/defaults/

WORKDIR "/etc/newrelic"

CMD ["/bin/bash", "newrelic-plugin-agent.sh"]

VOLUME ["/etc/newrelic/backends"]
