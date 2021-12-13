# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import abc
import importlib
import io
import os
import sys
import typing

from six.moves import filterfalse
from six.moves.collections_abc import Container

from ..base import FS
from ..wrapfs import WrapFS



__all__ = [
    'UniversalContainer',
    'NoWrapMeta',
    'unique',
    'import_from_names',
    'writable_path',
    'writable_stream'
]


class UniversalContainer(Container):
    """A container that contains everything.

    Example:
        >>> c = UniversalContainer()
        >>> 1 in c
        True
        >>> None in c
        True
        >>> c in c
        True

    """

    def __contains__(self, _):  # noqa: D105
        return True


class NoWrapMeta(getattr(typing, 'GenericMeta', abc.ABCMeta)):
    """Prevent classes from using `WrapFS` implementations of the `FS` methods.
    """

    def __new__(mcs, name, bases, attrs): # noqa: D102,D105
        _bases = bases + (FS,)
        exclude = ('__init__',)
        for base in _bases:
            if base is not WrapFS:
                for k,v in vars(base).items():
                    if callable(v) and k not in exclude:
                        attrs.setdefault(k, v)
        return super(NoWrapMeta, mcs).__new__(mcs, name, bases, attrs)


def unique(iterable, key=None):
        """Yield unique elements, preserving order.
        """
        seen = set()
        seen_add = seen.add
        if key is None:
            for element in filterfalse(seen.__contains__, iterable):
                seen_add(element)
                yield element
        else:
            for element in iterable:
                k = key(element)
                if k not in seen:
                    seen_add(k)
                    yield element


def import_from_names(*names):
    """Try to import the same function from various names.

    Example:
        >>> etree = import_from_names(
        ...     'lxml.etree',
        ...     'xml.etree.cElementTree',
        ...     'xml.etree.ElementTree'
        ... )
    """
    for name in names:
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    return None


def writable_path(path):
    """Test whether a path can be written to.
    """
    if os.path.exists(path):
        return os.access(path, os.W_OK)
    try:
        with open(path, 'w'):
            pass
    except (OSError, IOError):
        return False
    else:
        os.remove(path)
        return True


def writable_stream(handle):
    """Test whether a stream can be written to.
    """
    if isinstance(handle, io.IOBase) and sys.version_info >= (3, 5):
        return handle.writable()
    try:
        handle.write(b'')
    except (io.UnsupportedOperation, IOError):
        return False
    else:
        return True
