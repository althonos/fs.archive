# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import abc

from ..base import FS
from ..wrapfs import WrapFS


class ArchiveMeta(abc.ABCMeta):
    """Prevent classes from using `WrapFS` implementations.

    With this metaclass, the `ArchiveFS` methods use any other
    available implementation, falling back to `WrapFS` only in last
    resort (i.e., for `WrapFS.delegate_fs` and `WrapFS.delegate_path`
    if the derived object does not overload those methods). This
    prevents the wrapper from directly using the delegate filesystem
    methods, and instead forces it to use `FS` implementations that
    rely on the *essential* methods, which must be implemented.
    """

    def __new__(mcs, name, bases, attrs): # noqa: D102,D105
        _bases = bases + (FS,)
        exclude = ('__init__',)
        for base in _bases:
            if base is not WrapFS:
                for k,v in vars(base).items():
                    if callable(v) and k not in exclude:
                        attrs.setdefault(k, v)
        return super(ArchiveMeta, mcs).__new__(mcs, name, bases, attrs)
