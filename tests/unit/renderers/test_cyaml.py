# -*- coding: utf-8 -*-

# Import Python Libs
from __future__ import absolute_import, print_function, unicode_literals

# Import Salt Testing libs
from tests.support.mixins import LoaderModuleMockMixin
from tests.support.unit import TestCase

# Import Salt libs
import salt.renderers.cyaml as cyaml


class YAMLRendererTestCase(TestCase, LoaderModuleMockMixin):

    def setup_loader_modules(self):
        return {cyaml: {}}

    def test_yaml_render_string(self):
        data = 'string'
        result = cyaml.render(data)

        self.assertEqual(result, data)

    def test_yaml_render_unicode(self):
        data = '!!python/unicode python unicode string'
        result = cyaml.render(data)

        self.assertEqual(result, u'python unicode string')
