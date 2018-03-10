# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

from ...enums import Seek
from ...iotools import RawWrapper as BaseWrapper


class RawWrapper(BaseWrapper):  # noqa: D101

    def seek(self, pos, whence=Seek.set):  # noqa: D102
        if whence == Seek.set:
            if pos < 0:
                raise ValueError("Negative seek position {}".format(pos))
        elif whence == Seek.end:
            if pos > 0:
                raise ValueError("Positive seek position {}".format(pos))
        elif whence != Seek.current:
            raise ValueError(
                "Invalid whence ({}, should be {}, {} or {})".format(
                    whence, Seek.set, Seek.current, Seek.end
                )
            )
        self._f.seek(pos, whence)
        return self._f.tell()
