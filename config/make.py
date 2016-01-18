#!/usr/local/bin/python
import glob
import os
import sys
import yaml
import docker
from itertools import groupby
from collections import defaultdict
from copy import deepcopy
import logging
from fuzzywuzzy import fuzz
import argparse


def pprint(obj):
    return yaml.safe_dump(obj,
                          encoding='utf-8',
                          allow_unicode=True,
                          default_flow_style=False)


def merge_backends(base, overrides):
    merged = defaultdict(list, overrides)
    logging.debug("merging base and override")
    for name, item in zip_dict(*base.items()):
        match = filter(lambda oi: (oi['host'], oi['port']) == (item['host'], item['port']), overrides[name])
        if not match:
            logging.debug("adding base configuration for an '%s' item: %s", name, item)
            merged[name].append(item)
        else:
            logging.debug("found base configuration for an '%s' item. using it instead of the default: \n%s", name,
                          pprint(item))
            match[0].update(item)
    return merged


def zip_dict(*args):
    """
    creates a k,v tuple from dict items
    if the v is an iterable, returns a k, [ iterable_item ]
    """
    for k, v in args:
        if hasattr(v, '__iter__'):
            for items in v:
                yield k, items
        else:
            yield (k, v)


class AgentConfig(object):
    CONFIG_FILE = "config/newrelic-plugin-agent.cfg"
    BACKENDS_PATH = "backends"
    DEFAULTS_PATH = "defaults"

    def __init__(self, base_dir, dry_run=False):
        self._base_dir = base_dir
        self._config = yaml.load(file(os.path.join(args.dir, AgentConfig.CONFIG_FILE), "r"))
        self._cli = docker.Client("unix://var/run/docker.sock")

        if dry_run:
            self.save = lambda *a, **kw: logging.debug("! dry run. not saving: \n%s", pprint(self._config))

    def __str__(self):
        return pprint(self._config)

    def _get_defaults(self):
        """
        get all the default configurations from the defaults directory
        """
        for path in glob.glob("%s/*.yml" % os.path.join(self._base_dir, AgentConfig.DEFAULTS_PATH)):
            with open(os.path.join(self._base_dir, AgentConfig.DEFAULTS_PATH, path), "r") as f:
                logging.debug("loading %s from %s", path, f.name)
                default_config = yaml.load(f)
                name, _ = os.path.splitext(os.path.basename(path))
                default_config['name'] = name
                yield default_config

    def _default_configuration(self, backend_type):
        """
        get the default configuration for a given backend_type
        tries to find a backend with a similar name using fuzzy matching
        :param backend_type: the type of the agent backend
        """
        for default_config in self._get_defaults():
            logging.debug("fuzzy matching %s and %s", backend_type, default_config['name'])
            if fuzz.partial_ratio(backend_type, default_config['name']) > 90:
                logging.debug("found default configuration for backend type %s -> %s", backend_type,
                              default_config['name'])
                return default_config

    def _generate_default_configuration(self, container, default_config):
        """
        generates a default config based on the given default configuration
        :param default_config:
        :param container:
        """

        public_ports = self._cli.port(container['Id'], default_config['port'])

        if not public_ports:
            logging.debug("couldn't find public ports for container id: %s", container['Id'])
            return

        container_name = container['Names'][0].strip("/")
        default_config['name'] = "{container_name} @ {host}".format(host=default_config['host'],
                                                                    container_name=container_name)
        default_config['port'] = int(public_ports[0]['HostPort'])
        logging.debug("generated default config for containe id: %s: \n%s", container['Id'], pprint(default_config))
        return default_config

    def discover(self):
        """
        tries to discover backends to monitor from images running on this server
        """
        discovered = defaultdict(list)
        containers = sorted(self._cli.containers(), key=lambda c: c['Image'])
        host = self._cli.info()['Name']

        for image_name, containers in groupby(containers, key=lambda c: c['Image']):
            logging.debug("found running images for: %s", image_name)
            default_config = self._default_configuration(image_name)
            if not default_config:
                logging.debug("image: %s doesn't have a default config. skipping.", image_name)
                continue
            name = default_config.pop('name')
            default_config['host'] = host
            configurations = (self._generate_default_configuration(c, deepcopy(default_config)) for c in containers)
            discovered[name] = filter(None, configurations)

        return discovered

    def base_backends(self):
        """
        finds all the base backends configured by the user
        """
        base = defaultdict(list)
        for path in glob.glob("%s/*.yml" % os.path.join(self._base_dir, AgentConfig.BACKENDS_PATH)):
            with open(os.path.join(self._base_dir, AgentConfig.BACKENDS_PATH, path)) as f:
                name, _ = os.path.splitext(os.path.basename(path))
                conf = yaml.load(f)
                base[name] = conf if isinstance(conf, list) else [conf]
                logging.debug("loaded base backend %s: \n%s", path, pprint(base[path]))
        return base

    def set_application(self, app_name, app):
        """
        set the application and its values
        :param app_name: the name of the app
        :param app: the app to set
        """
        logging.debug("setting application: %s, app: \n%s", app_name, pprint(app))
        self._config['Application'][app_name] = app

    def set_license(self, key):
        """
        set the license of the application
        """
        logging.debug("setting application license: %s", key)
        self._config['Application']['license_key'] = key


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--key", type=str,
                        default=os.environ.get("NEWRELIC_KEY"),
                        help="newrelic license key")
    parser.add_argument("-d", "--dir", type=str,
                        default="/etc/newrelic",
                        help="base directory for config / default configurations")

    parser.add_argument("--verbose", action="store_true", default=bool(os.environ.get("DEBUG", False)))

    parser.add_argument("--dry-run", action="store_true", default=bool(os.environ.get("DRY_RUN", False)))

    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    if args.verbose:
        logging.basicConfig(format='$ %(message)s')
        logging.root.setLevel(logging.DEBUG)

    config = AgentConfig(args.dir, args.dry_run)
    if not args.key:
        logging.fatal("you need to set the NEWRELIC_KEY environment variable!")
        sys.exit(2)

    config.set_license(args.key)
    for backend_name, backends in merge_backends(config.base_backends(), config.discover()).iteritems():
        config.set_application(backend_name, backends)

    print(config)
