# -*- coding: utf-8 -*-
import time
import copy
from collections import defaultdict

from amplify.agent import Singleton


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class StatsdContainer(Singleton):
    def __init__(self, *args, **kwargs):
        self.clients = defaultdict(dict)

    def register(self, type, object_id, client):
        """
        Registers StatsdClient

        :param type: object type (prefix)
        :param object_id: object id
        :param client: StatsdClient
        """
        self.clients[type][object_id] = client

    def unregister(self, type, object_id):
        """
        Unregisters StatsdClient client

        :param type: object type (prefix)
        :param object_id: object id
        """
        del self.clients[type][object_id]

    def flush(self, type):
        result = {}
        for object_id, client in self.clients.get(type, {}).iteritems():
            data = client.flush()
            if data:
                result[object_id] = data
        return result


class StatsdClient(object):
    def __init__(self, address=None, port=None, prefix=None, interval=None, object=None):
        # Import context as a class object to avoid circular import on statsd.  This could be refactored later.
        from amplify.agent.context import context
        self.context = context

        self.address = address
        self.port = port
        self.prefix = prefix
        self.object = object
        self.interval = interval
        self.current = defaultdict(dict)
        self.delivery = defaultdict(dict)

    def average(self, name, value):
        """
        Same thing as histogram but without p95

        :param name:  metric name
        :param value:  metric value
        """
        metric_name = '%s.%s' % (self.prefix, name)

        if metric_name in self.current['average']:
            self.current['average'][metric_name].append(value)
        else:
            self.current['average'][metric_name] = [value]

    def timer(self, name, value):
        """
        Histogram with 95 percentile

        The algorithm is as follows:

        Collect all the data samples for a period of time (commonly a day, a week, or a month).
        Sort the data set by value from highest to lowest and discard the highest 5% of the sorted samples.
        The next highest sample is the 95th percentile value for the data set.

        :param name: metric name
        :param value: metric value
        """
        metric_name = '%s.%s' % (self.prefix, name)

        if metric_name in self.current['timer']:
            self.current['timer'][metric_name].append(value)
        else:
            self.current['timer'][metric_name] = [value]

    def incr(self, name, value=None, rate=None):
        """
        Simple counter with rate
        :param name: metric name
        :param value: metric value
        :param rate: rate
        """
        timestamp = int(time.time())
        metric_name = '%s.%s' % (self.prefix, name)

        if value is None:
            value = 1

        # new metric
        if metric_name not in self.current['counter']:
            self.current['counter'][metric_name] = [[timestamp, value]]
            return

        # metric exists
        slots = self.current['counter'][metric_name]
        last_stamp, last_value = slots[-1]

        # if rate is set then check it's time
        if self.interval and rate:
            sample_duration = self.interval * rate
            # write to current slot
            if timestamp < last_stamp + sample_duration:
                self.current['counter'][metric_name][-1] = [last_stamp, last_value + value]
            else:
                self.current['counter'][metric_name].append([last_stamp, value])
        else:
            self.current['counter'][metric_name][-1] = [last_stamp, last_value + value]

    def agent(self, name, value):
        """
        Agent metrics
        :param name: metric
        :param value: value
        """
        timestamp = int(time.time())
        metric_name = 'amplify.agent.%s' % name
        self.current['gauge'][metric_name] = [(timestamp, value)]

    def gauge(self, name, value, delta=False, prefix=False):
        """
        Gauge
        :param name: metric name
        :param value: metric value
        :param delta: metric delta (applicable only if we have previous values)
        """
        timestamp = int(time.time())
        metric_name = '%s.%s' % (self.prefix, name)

        if metric_name in self.current['gauge']:
            if delta:
                last_stamp, last_value = self.current['gauge'][metric_name][-1]
                new_value = last_value + value
            else:
                new_value = value
            self.current['gauge'][metric_name].append((timestamp, new_value))
        else:
            self.current['gauge'][metric_name] = [(timestamp, value)]

    def flush(self):
        if not self.current:
            return

        results = {}
        delivery = copy.deepcopy(self.current)
        self.current = defaultdict(dict)

        # histogram
        if 'timer' in delivery:
            timers = {}
            timestamp = int(time.time())
            for metric_name, metric_values in delivery['timer'].iteritems():
                if len(metric_values):
                    metric_values.sort()
                    length = len(metric_values)
                    timers['G|%s' % metric_name] = [[timestamp, sum(metric_values) / float(length)]]
                    timers['C|%s.count' % metric_name] = [[timestamp, length]]
                    timers['G|%s.max' % metric_name] = [[timestamp, metric_values[-1]]]
                    timers['G|%s.median' % metric_name] = [[timestamp, metric_values[int(round(length / 2 - 1))]]]
                    timers['G|%s.pctl95' % metric_name] = [[timestamp, metric_values[-int(round(length * .05))]]]
            results['timer'] = timers

        # counters
        if 'counter' in delivery:
            counters = {}
            for k, v in delivery['counter'].iteritems():
                # Aggregate all observed counters into a single record.
                last_stamp = v[-1][0]  # Use the oldest timestamp.
                total_value = 0
                for timestamp, value in v:
                    total_value += value

                # Condense the list of lists 'v' into a list of a single element.  Remember that we are using lists
                # instead of tuples because we need mutability during self.incr().
                counters['C|%s' % k] = [[last_stamp, total_value]]

            results['counter'] = counters

        # gauges
        if 'gauge' in delivery:
            gauges = {}
            for k, v in delivery['gauge'].iteritems():
                # Aggregate all observed gauges into a single record.
                last_stamp = v[-1][0]  # Use the oldest timestamp.
                total_value = 0
                for timestamp, value in v:
                    total_value += value

                # Condense list of tuples 'v' into a list of a single tuple using an average value.
                gauges['G|%s' % k] = [(last_stamp, float(total_value)/len(v))]
            results['gauge'] = gauges

        # avg
        if 'average' in delivery:
            averages = {}
            timestamp = int(time.time())  # Take a new timestamp here because it is not collected previously.
            for metric_name, metric_values in delivery['average'].iteritems():
                if len(metric_values):
                    length = len(metric_values)
                    averages['G|%s' % metric_name] = [[timestamp, sum(metric_values) / float(length)]]
            results['average'] = averages

        return {
            'object': self.object.definition,
            'metrics': results,
            'agent_version': self.context.version
        }
