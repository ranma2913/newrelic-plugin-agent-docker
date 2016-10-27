FROM gici/python
MAINTAINER Oded Lazar <odedlaz@gmail.com>

# needed packages
RUN apt-get update && apt-get install -y -qq supervisor libpq-dev git && \
    rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/ShaharLevin/newrelic-plugin-agent.git /tmp/newrelic

# newrelic-plugin-agent requirements
RUN pip install psycopg2 \
    docker-py \
    fuzzywuzzy \
    python-Levenshtein \
    python-json-logger

RUN cd /tmp/newrelic/; python /tmp/newrelic/setup.py install

#newrelic-plugin-agent

# supervisor
RUN mkdir -p /etc/supervisor/conf.d/ && \
    mkdir -p /var/log/supervisor/

ADD supervisor/supervisord.conf /etc/supervisor/supervisord.conf
ADD supervisor/supervisord-*.conf /etc/supervisor/conf.d/

# newrelic-plugin-agent
ADD newrelic-plugin-agent-discover.sh run.py /etc/newrelic/
ADD config/newrelic-plugin-agent.cfg config/make.py /etc/newrelic/config/

# add default configurations
ADD defaults /etc/newrelic/defaults/
ADD plugins /etc/newrelic/plugins/
WORKDIR "/etc/newrelic"

VOLUME ["/etc/newrelic/backends"]

CMD ["supervisord"]
