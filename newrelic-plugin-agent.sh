#!/bin/sh

python config/make.py > /etc/newrelic/newrelic-plugin-agent.cfg
supervisord

while [ true ]
do
    python config/make.py > /etc/newrelic/newrelic-plugin-agent.cfg.new
    diff -q /etc/newrelic/newrelic-plugin-agent.cfg.new /etc/newrelic/newrelic-plugin-agent.cfg
    if [ $? -eq 1 ]; then
        echo "config has changed. restarting the app!"
        mv /etc/newrelic/newrelic-plugin-agent.cfg.new /etc/newrelic/newrelic-plugin-agent.cfg
        supervisorctl restart newrelic-plugin-agent
    fi
    sleep 1
done
