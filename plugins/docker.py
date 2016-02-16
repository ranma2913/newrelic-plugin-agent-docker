"""
Redis plugin polls Redis for stats

"""
from __future__ import absolute_import
import logging
import os
import stat
from docker import Client as client
import re

from newrelic_plugin_agent.plugins import base

LOGGER = logging.getLogger(__name__)
print(__name__)

class Docker(base.JSONStatsPlugin):

    GUID = 'com.senexx.newrelic_docker_agent'
    FLOAT_REGEX = re.compile("^(?P<size>\d*.?\d+)\s(?P<unit>gb|mb|kb)", re.IGNORECASE)
    CONVERT_UNIT = {"kb": lambda x: x / 1000**2,
                    "mb": lambda x: x / 1000,
                    "gb": lambda x: x}

    def add_datapoints(self, stats):
        """Add all of the data points for a node

        :param dict stats: all of the nodes

        """
        if stats.get("Driver", "") == "devicemapper":
            for key, value in stats['DriverStatus']:
                match = Docker.FLOAT_REGEX.match(value)
                if not match:
                    continue
                size, unit = match.groups()
                metric_name = "/".join(key.split(" "))
                value = Docker.CONVERT_UNIT[unit.lower()](float(size))
                self.add_gauge_value(metric_name, 'gb', value)

        self.add_gauge_value("Containers/Count", 'containers', stats.get("Containers"))
        for status in ["Paused", "Running", "Stopped"]:
            metric_name = "/".join(["Containers", status])
            value = "".join(["Containers", status])
            if value not in stats:
                continue
            self.add_gauge_value(metric_name,
                                 'containers',
                                 stats.get(value))

    def _connect(self):
        """Top level interface to create a socket and connect it to the
        redis daemon.

        :rtype: socket

        """
        base_url = self.config.get("path")
        version = self.config.get("version", "auto")
        timeout = self.config.get("timeout", 5)
        tls = self.config.get("tls", False)
        LOGGER.debug("connecting to docker at: %s | version: %s | timeout: %s | tls: %s",
                     base_url,
                     version,
                     timeout,
                     tls)
        return client(base_url=base_url,
                             version=version,
                             timeout=timeout,
                             tls=tls)

    def fetch_data(self):
        """Loop in and read in all the data until we have received it all.

        :param  socket connection: The connection
        :rtype: dict

        """
        connection = self._connect()
        return connection.info()
