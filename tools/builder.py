#!/usr/bin/python
# -*- coding: utf-8 -*-
import os

from builders import deb, rpm

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"

if __name__ == '__main__':
    if os.path.isfile('/etc/debian_version'):
        deb.build()
    elif os.path.isfile('/etc/redhat-release'):
        rpm.build()
    else:
        print "sorry, it will be done later\n"
