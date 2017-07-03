# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import importlib

def import_from_names(*names):
    for name in names:
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    return None
