#!/bin/sh
set -e
python config/make.py
newrelic-plugin-agent -f -c "/etc/newrelic/config/newrelic-plugin-agent.cfg"
