FROM gici/python
MAINTAINER Oded Lazar <odedlaz@gmail.com>

# needed packages
RUN apt-get update && apt-get install -y -qq supervisor libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# newrelic-plugin-agent requirements
RUN pip install psycopg2 \
    newrelic-plugin-agent \
    docker-py \
    fuzzywuzzy \
    python-Levenshtein

# supervisor
RUN mkdir -p /etc/supervisor/conf.d/ && \
    mkdir -p /var/log/supervisor/

ADD supervisord.conf /etc/supervisor/supervisord.conf
ADD supervisord-*.conf /etc/supervisor/conf.d/


# newrelic-plugin-agent
ADD newrelic-plugin-agent-discover.sh /etc/newrelic/
ADD config/newrelic-plugin-agent.cfg config/make.py /etc/newrelic/config/

# add default configurations
ADD defaults /etc/newrelic/defaults/

WORKDIR "/etc/newrelic"

VOLUME ["/etc/newrelic/backends"]

CMD ["supervisord"]
