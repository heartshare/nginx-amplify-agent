# -*- coding: utf-8 -*-
import os

from amplify.agent.config.abstract import AbstractConfig

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class Config(AbstractConfig):
    filename = None

    config = dict(
        daemon=dict(
            pid=os.getcwd() + '/amplify_agent.pid',
        ),
        containers=dict(
        ),
        cloud=dict(
            push_interval=20.0,
            api_url=None,
            api_timeout=5.0,
            verify_ssl=False,
            gzip=6,
        ),
        credentials=dict(
            api_key=None,
            uuid=None,
            hostname=None
        )
    )

    config_changes = dict()

    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        self.apply(self.config_changes)


class DevelopmentConfig(Config):
    write_new = False
    filename = 'etc/agent.conf.development'

    config_changes = dict(
        cloud=dict(
            api_url='http://%s:%s/1.0' % (
                os.environ.get('RECEIVER_PORT_5000_TCP_ADDR'),
                os.environ.get('RECEIVER_PORT_5000_TCP_PORT')
            ),
            verify_ssl=False
        ),
        credentials=dict(
            api_key='DEFAULT'
        ),
        daemon=dict(
            pid='/var/run/amplify_agent.pid'
        )
    )


class SandboxConfig(Config):
    write_new = True

    config_changes = dict(
        cloud=dict(
            api_url='http://localhost:5001/1.0',
            verify_ssl=False
        ),
        credentials=dict(
            api_key='DEFAULT'
        ),
    )


class ProductionConfig(Config):
    write_new = True


