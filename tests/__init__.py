# coding: utf-8
"""Tests package of `fs.archive`.
"""
from __future__ import unicode_literals
from __future__ import absolute_import

import fs
import os
import pkg_resources
import six

# Add the local code directory to the `fs` module path
fs.__path__.insert(0, os.path.realpath(
    os.path.join(__file__, '..', '..', 'fs')))
