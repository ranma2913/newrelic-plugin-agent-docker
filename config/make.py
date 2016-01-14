#!/usr/local/bin/python
import os
import sys
import yaml

CONFIG_FILEPATH="/etc/newrelic/config/newrelic-plugin-agent.cfg"
BACKENDS_PATH="/etc/newrelic/backends"

if __name__ == "__main__":

    key = os.environ.get("NEWRELIC_KEY")
    if not key:
        print("you need to set the NEWRELIC_KEY environment variable!")
        sys.exit(1)

    backends = os.listdir(BACKENDS_PATH)
    if not backends:
        print("there aren't any backends in {}".format(BACKENDS_PATH))
        sys.exit(2)

    with open(CONFIG_FILEPATH, "rw") as f:
        config = yaml.load(f)

    config['Application']['license_key'] = key

    for backend_name in os.listdir(BACKENDS_PATH):
        with open(os.path.join(BACKENDS_PATH, backend_name)) as f:
            backend = yaml.load(f)
        config['Application'][backend_name] = backend

    with open(CONFIG_FILEPATH, "w") as f:
        f.write(yaml.dump(config, default_flow_style=False))
