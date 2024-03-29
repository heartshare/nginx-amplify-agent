# -*- coding: utf-8 -*-
import os

from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.containers.nginx.config.parser import NginxConfigParser, IGNORED_DIRECTIVES


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


simple_config = os.getcwd() + '/test/fixtures/nginx/simple/nginx.conf'
complex_config = os.getcwd() + '/test/fixtures/nginx/complex/nginx.conf'
huge_config = os.getcwd() + '/test/fixtures/nginx/huge/nginx.conf'
broken_config = os.getcwd() + '/test/fixtures/nginx/broken/nginx.conf'
rewrites_config = os.getcwd() + '/test/fixtures/nginx/rewrites/nginx.conf'
map_lua_perl = os.getcwd() + '/test/fixtures/nginx/map_lua_perl/nginx.conf'
ssl_config = os.getcwd() + '/test/fixtures/nginx/ssl/nginx.conf'


class ParserTestCase(BaseTestCase):

    def test_parse_simple(self):
        cfg = NginxConfigParser(simple_config)
        tree = cfg.simplify()
        indexed_tree = cfg.tree

        # common structure
        assert_that(tree, has_key('http'))
        assert_that(tree, has_key('events'))

        # http
        http = tree['http']
        assert_that(http, has_key('server'))
        assert_that(http, has_key('types'))
        assert_that(http, has_key('include'))
        assert_that(http['server'], is_(instance_of(list)))
        assert_that(http['server'], has_length(2))

        # server
        server = http['server'][1]
        assert_that(server, has_key('listen'))
        assert_that(server, has_key('location'))
        assert_that(server['location'], is_(instance_of(dict)))

        # location
        location = server['location']
        assert_that(location, has_key('/basic_status'))

        # nested location
        assert_that(http['server'][0]['location']['/'], has_key('location'))

        # included mimes
        mimes = http['types']
        assert_that(mimes, has_key('application/java-archive'))

        # check index tree
        worker_connections_index = indexed_tree['events'][0]['worker_connections'][1]
        basic_status_index = indexed_tree['http'][0]['server'][1][0]['location']['/basic_status'][1]
        stub_status_in_basic_index = indexed_tree['http'][0]['server'][1][0]['location']['/basic_status'][0]['stub_status'][1]
        proxy_pass_index = indexed_tree['http'][0]['server'][0][0]['location']['/'][0]['proxy_pass'][1]

        assert_that(cfg.index[worker_connections_index], equal_to((0, 6)))  # root file, line number 6
        assert_that(cfg.index[basic_status_index], equal_to((0, 67)))  # root file, line number 65
        assert_that(cfg.index[stub_status_in_basic_index], equal_to((0, 69)))  # root file, line number 66
        assert_that(cfg.index[proxy_pass_index], equal_to((2, 13)))  # third loaded file, line number 13

    def test_parse_huge(self):
        cfg = NginxConfigParser(huge_config)
        tree = cfg.simplify()
        indexed_tree = cfg.tree

        # common structure
        assert_that(tree, has_key('http'))
        assert_that(tree, has_key('events'))

        # http
        http = tree['http']
        assert_that(http, has_key('server'))
        assert_that(http, has_key('include'))
        assert_that(http['server'], is_(instance_of(list)))
        assert_that(http['server'], has_length(8))

        # map
        http_map = http['map']
        assert_that(http_map, equal_to({'$dirname $diruri': {'default': '"dirindex.html"', 'include': ['"dir.map"']}}))

        # check index tree
        books_location_index = indexed_tree['http'][0]['server'][2][0]['location']['/books/'][1]
        assert_that(cfg.index[books_location_index], equal_to((0, 134)))  # root file, line number 134

    def test_parse_complex(self):
        cfg = NginxConfigParser(complex_config)
        tree = cfg.simplify()
        indexed_tree = cfg.tree

        # common structure
        assert_that(tree, has_key('http'))
        assert_that(tree, has_key('events'))

        # http
        http = tree['http']
        assert_that(http, has_key('server'))
        assert_that(http, has_key('upstream'))
        assert_that(http, has_key('include'))
        assert_that(http['server'], is_(instance_of(list)))
        assert_that(http['server'], has_length(11))

        # upstream
        upstream = http['upstream']
        assert_that(upstream, has_length(2))

        # ifs
        for server in http['server']:
            if server.get('listen', '') == '127.0.0.3:10122':
                assert_that(server, has_item('if'))

        # check index tree
        x1_location_index = indexed_tree['http'][0]['server'][0][0]['location']['/'][1]
        x2_return_index = indexed_tree['http'][0]['server'][1][0]['location']['/'][0]['return'][1]
        assert_that(cfg.index[x1_location_index], equal_to((0, 8)))  # root file, line number 8
        assert_that(cfg.index[x2_return_index], equal_to((0, 9)))  # root file, line number 9

    def test_parse_rewrites(self):
        cfg = NginxConfigParser(rewrites_config)
        tree = cfg.simplify()

        # common structure
        assert_that(tree, has_key('http'))

        # http
        http = tree['http']
        assert_that(http, has_key('server'))

        # rewrites
        for server in http['server']:
            if server.get('server_name', '') == 'mb.some.org localhost melchior melchior.some.org':
                assert_that(server, has_item('rewrite'))

    def test_parse_map_lua_perl(self):
        cfg = NginxConfigParser(map_lua_perl)
        tree = cfg.simplify()

        # common structure
        assert_that(tree, has_key('http'))

        # http
        http = tree['http']
        assert_that(http, has_key('server'))
        assert_that(http, has_key('map'))
        assert_that(http, has_key('perl_set'))

        # lua
        for server in http['server']:
            if server.get('server_name', '') == '127.0.0.1':
                assert_that(server, has_item('lua_shared_dict'))

                for location, data in server['location'].iteritems():
                    if location == '= /some/':
                        assert_that(data, has_item('rewrite_by_lua'))

    def test_parse_ssl(self):
        """
        This test case specifically checks to see that none of the excluded directives (SSL focused) are parsed.
        """

        cfg = NginxConfigParser(ssl_config)
        tree = cfg.simplify()

        assert_that(tree, has_key('server'))

        # ssl
        for directive in IGNORED_DIRECTIVES:
            assert_that(tree['server'][1], is_not(has_item(directive)))
