# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools

import six


def iget(it, position):
    try:
        return next(itertools.islice(it, position, position+1))
    except StopIteration:
        six.raise_from(IndexError('iterator index out of range'), None)
