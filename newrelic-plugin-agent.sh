#!/bin/sh

touch /etc/newrelic/newrelic-plugin-agent.cfg
while [ true ]
do
    python config/make.py > /etc/newrelic/newrelic-plugin-agent.cfg.new
    diff -q /etc/newrelic/newrelic-plugin-agent.cfg.new /etc/newrelic/newrelic-plugin-agent.cfg
    if [ $? -eq 1 ]; then

        echo "config has changed. restarting the app!"
        mv /etc/newrelic/newrelic-plugin-agent.cfg.new /etc/newrelic/newrelic-plugin-agent.cfg
        kill `pidof python`
        newrelic-plugin-agent -c "/etc/newrelic/newrelic-plugin-agent.cfg"
    fi
    sleep 1
done