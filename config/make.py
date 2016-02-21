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

def one(iterable):
    """
    return one or None
    """
    if len(iterable) <= 0:
         return
    if len(iterable) > 1:
        return
    return iterable[0]

def fuzzy_in(text, iterable, ratio=90):
    """
    fuzzy searches inside an iterable
    """
    for item in iterable:
        if fuzz.partial_ratio(text, item) > ratio:
            return True
    return False

class DockerClient(docker.Client):
    def __init__(self, *args, **kwargs):
        super(DockerClient, self).__init__(*args, **kwargs)
        self.hostname = self.info()['Name']
        self.containers = self.containers()
        self.images = self.images()

    def get_image_by_name(self, image_name):
        """
        gets an image by the name of the image
        """
        image_id = filter(lambda x: fuzzy_in(image_name, x['RepoTags']), self.images)[0]
        # the following has been added in later versions of the docker api
        # for now we only have the old, ugly way of getting the image id
        # image_id = [x['ImageID'] for x in self.containers if x['Image'] == image_name][0]
        return self.get_image_by_id(image_id)

    def get_image_by_id(self, image_id):
        """
        get an image by its id
        """
        image = one(filter(lambda x: x['Id'] == image_id, self.images))
        return image

    def image_labels(self, image_id):
        return self.inspect_image(image_id).get('ContainerConfig', {}).get('Labels', {})

def merge_backends(base, overrides):
    """
    merged the backends using the following merge policy:
    if a backend exists in the backends directory -> use it.
    otherwise, use the discovered one.
    """
    merged = defaultdict(list, base)
    logging.debug("merging base and override")
    for key, value in overrides.iteritems():
        if key in base:
            logging.debug("{key} already exist in base backends. not discovering.".format(key=key))
            continue
        logging.debug("{key} wasn't configured, using discovered one: {value}".format(key=key, value=value))
        merged[key] = value
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

    def __init__(self, base_dir):
        """
        :param base_dir: the directory to find the config dir
        """
        self._base_dir = base_dir
        self._cli = DockerClient("unix://var/run/docker.sock", version="auto")
        self._config = yaml.load(file(os.path.join(args.dir,
                                                   AgentConfig.CONFIG_FILE),
                                      "r"))

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

    def _generate_default_configuration(self, container, default_config):
        """
        generates a default config based on the given default configuration
        :param default_config:
        :param container:
        """
        public_ports = self._cli.port(container['Id'], default_config.get('port', -1))

        if not public_ports:
            logging.debug("couldn't find public ports for container id: %s", container['Id'])

        container_name = container['Names'][0].strip("/")
        default_config['name'] = "{container_name} @ {host}".format(host=default_config['host'],
                                                                    container_name=container_name)
        if public_ports:
            default_config['port'] = int(public_ports[0]['HostPort'])
        logging.debug("generated default config for container id: %s: \n%s", container['Id'], pprint(default_config))
        return default_config

    def _discover_by_image_name(self, image_name, image):
        """
        get the default configuration for a given image
        tries to find a backend with a similar name using fuzzy matching
        """
        for default_config in self._get_defaults():
            logging.debug("fuzzy matching %s and %s", image_name, default_config['name'])
            if fuzz.partial_ratio(image_name, default_config['name']) > 90:
                return default_config

    def _discover_by_metadata(self, image_name, image):
        """
        discovers default configuration based on container metadata label com.newrelic.plugin
        """
        labels = self._cli.image_labels(image['Id'])
        logging.debug("discovering using metadata for %s, labels: %s", image_name, pprint(labels))
        if not labels or "com.newrelic.plugin" not in labels:
            return
        plugin_name = labels["com.newrelic.plugin"]

        logging.debug("%s has a plugin label: %s",
                      image_name,
                      plugin_name)
        for default_config in self._get_defaults():
            if fuzz.partial_ratio(plugin_name, default_config['name']) > 90:
                return default_config

    def _find_plugin_configuration(self, image_name):
        """
        try to find the plugin using its image name
        """
        image = self._cli.get_image_by_name(image_name)
        if not image:
            logging.debug("couldn't find image %s by name", image_name)
            return

        for f in [self._discover_by_metadata, self._discover_by_image_name]:
            default_config = f(image_name, image)
            if default_config:
                logging.debug("found default configuration for image name %s -> %s",
                              image_name,
                              default_config['name'])
                return default_config
        logging.debug("image: %s doesn't have a default config.", image_name)

    def discover(self):
        """
        tries to discover backends to monitor from images running on this server
        """
        discovered = defaultdict(list)
        containers = sorted(self._cli.containers, key=lambda c: c['Image'])
        for image_name, containers in groupby(containers, key=lambda c: c['Image']):
            logging.debug("trying to discover: %s", image_name)
            default_config = self._find_plugin_configuration(image_name)
            if not default_config:
                logging.debug("couldn't discover for: %s", image_name)
                continue
            name = default_config.pop('name')
            default_config['host'] = self._cli.hostname
            configurations = (self._generate_default_configuration(c, deepcopy(default_config)) for c in containers)
            discovered[name] = filter(None, configurations)

        return discovered

    def base_backends(self):
        """
        finds all the base backends configured by the user
        """
        base = defaultdict(list)
        backends_dir = os.path.join(self._base_dir, AgentConfig.BACKENDS_PATH)
        for path in glob.glob("%s/*.yml" % backends_dir):
            filepath = os.path.join(self._base_dir,
                                    AgentConfig.BACKENDS_PATH,
                                    path)
            with open(filepath) as f:
                name, _ = os.path.splitext(os.path.basename(path))
                conf = yaml.load(f)
                base[name] = conf if isinstance(conf, list) else [conf]
                logging.debug("loaded base backend %s: \n%s",
                              path,
                              pprint(base[name]))
        return base

    def set_application(self, app_name, app):
        """
        set the application and its values
        :param app_name: the name of the app
        :param app: the app to set
        """
        app = app if isinstance(app, list) else [app]
        logging.debug("setting application: %s, app: \n%s",
                      app_name,
                      pprint(app))
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

    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    if args.verbose:
        logging.basicConfig(format='$ %(message)s')
        logging.root.setLevel(logging.DEBUG)

    config = AgentConfig(args.dir)
    if not args.key:
        logging.fatal("you need to set the NEWRELIC_KEY environment variable!")
        sys.exit(2)
    config.set_license(args.key)
    config.set_application("docker", {'name': "docker @ {}".format(config._cli.hostname)})
    backends = merge_backends(config.base_backends(), config.discover())
    for backend_name, backends in backends.iteritems():
        config.set_application(backend_name, backends)

    print(config)
