# -*- coding: utf-8 -*-
import os
import sys
import time
import thread
from itertools import cycle

from amplify.agent import Singleton
from amplify.agent.statsd import StatsdContainer
from amplify.agent.eventd import EventdContainer
from amplify.agent.metad import MetadContainer
from amplify.agent.configd import ConfigdContainer


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"

sys.tracebacklimit = 10000
sys.setrecursionlimit(2048)


class Context(Singleton):
    def __init__(self):
        self.pid = os.getpid()

        self.version = '0.23-1'  # Major.Minor-Build

        self.default_log = None
        self.app_name = None
        self.app_config = None
        self.statsd = StatsdContainer()
        self.eventd = EventdContainer()
        self.metad = MetadContainer()
        self.configd = ConfigdContainer()
        self.top_object = None
        self.ids = {}
        self.action_ids = {}

        self.start_time = int(time.time())

        self.setup_thread_id()
        self._setup_environment()

    def setup(self, **kwargs):
        self._setup_app_config(**kwargs)
        self._setup_app_logs(**kwargs)
        self._setup_host_details()

    def _setup_environment(self):
        """
        Setup common environment vars
        """
        self.environment = os.environ.get('AMPLIFY_ENVIRONMENT', 'production')

    def _setup_app_config(self, **kwargs):
        self.app_name = kwargs.get('app')
        self.app_config = kwargs.get('app_config')

        from amplify.agent.util import configreader
        if self.app_config is None:
            self.app_config = configreader.read('app', config_file=kwargs.get('config_file'))
        else:
            configreader.CONFIG_CACHE['app'] = self.app_config

        if kwargs.get('pid_file'):
            self.app_config['daemon']['pid'] = kwargs.get('pid_file')

    def _setup_app_logs(self, **kwargs):
        from amplify.agent.util import logger
        logger.setup(self.app_config.filename)
        self.default_log = logger.get('%s-default' % self.app_name)

    def _setup_host_details(self):
        from amplify.agent.util.host import hostname, uuid
        self.hostname = hostname()
        self.uuid = uuid()

    def get_file_handlers(self):
        return [
            self.default_log.handlers[0].stream,
        ]

    def inc_action_id(self):
        thread_id = thread.get_ident()
        self.action_ids[thread_id] = '%s_%s' % (thread_id, self.ids[thread_id].next())

    def setup_thread_id(self):
        thread_id = thread.get_ident()
        self.ids[thread_id] = cycle(xrange(10000, 10000000))
        self.action_ids[thread_id] = '%s_%s' % (thread_id, self.ids[thread_id].next())

    @property
    def log(self):
        return self.default_log


context = Context()
