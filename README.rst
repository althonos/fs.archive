``fs.archive``
==============

|Source| |PyPI| |Travis| |Codecov| |Codacy| |Format| |License|

.. |Codacy| image:: https://img.shields.io/codacy/grade/eadf418db5a84efd9fa1b470529dcad6/master.svg?style=flat-square&maxAge=300
   :target: https://www.codacy.com/app/althonos/fs.archive/dashboard

.. |Travis| image:: https://img.shields.io/travis/althonos/fs.archive/master.svg?style=flat-square&maxAge=300
   :target: https://travis-ci.org/althonos/fs.archive/branches

.. |Codecov| image:: https://img.shields.io/codecov/c/github/althonos/fs.archive/master.svg?style=flat-square&maxAge=300
   :target: https://codecov.io/gh/althonos/fs.archive

.. |PyPI| image:: https://img.shields.io/pypi/v/fs.archive.svg?style=flat-square&maxAge=300
   :target: https://pypi.python.org/pypi/fs.archive

.. |Format| image:: https://img.shields.io/pypi/format/fs.archive.svg?style=flat-square&maxAge=300
   :target: https://pypi.python.org/pypi/fs.archive

.. |Versions| image:: https://img.shields.io/pypi/pyversions/fs.archive.svg?style=flat-square&maxAge=300
   :target: https://travis-ci.org/althonos/fs.archive

.. |License| image:: https://img.shields.io/pypi/l/fs.archive.svg?style=flat-square&maxAge=300
   :target: https://choosealicense.com/licenses/mit/

.. |Source| image:: https://img.shields.io/badge/source-GitHub-303030.svg?maxAge=300&style=flat-square
   :target: https://github.com/althonos/fs.archive


Requirements
------------

+-------------------+-----------------+-------------------+--------------------+
| **pyfilesystem2** | |PyPI fs|       | |Source fs|       | |License fs|       |
+-------------------+-----------------+-------------------+--------------------+
| **six**           | |PyPI six|      | |Source six|      | |License six|      |
+-------------------+-----------------+-------------------+--------------------+

.. |License six| image:: https://img.shields.io/pypi/l/six.svg?maxAge=300&style=flat-square
   :target: https://choosealicense.com/licenses/mit/

.. |Source six| image:: https://img.shields.io/badge/source-GitHub-303030.svg?maxAge=300&style=flat-square
   :target: https://github.com/benjaminp/six

.. |PyPI six| image:: https://img.shields.io/pypi/v/six.svg?maxAge=300&style=flat-square
   :target: https://pypi.python.org/pypi/six

.. |License fs| image:: https://img.shields.io/badge/license-MIT-blue.svg?maxAge=300&style=flat-square
   :target: https://choosealicense.com/licenses/mit/

.. |Source fs| image:: https://img.shields.io/badge/source-GitHub-303030.svg?maxAge=300&style=flat-square
   :target: https://github.com/PyFilesystem/pyfilesystem2

.. |PyPI fs| image:: https://img.shields.io/pypi/v/fs.svg?maxAge=300&style=flat-square
   :target: https://pypi.python.org/pypi/fs


Installation
------------

Install directly from PyPI, using `pip <https://pip.pypa.io/>`_ ::

    pip install fs.archive

Additional features
^^^^^^^^^^^^^^^^^^^

``fs.archive`` also provides the following `extras
<https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies>`_:

*all*
    install all the extras listed below.

*tar.xz*
    support for ``xz`` compressed tar files. Requires the additional
    `backports.lzma <https://pypi.python.org/pypi/backports.lzma>`_
    module in Python 2, but is available natively in Python 3.

*iso*
    pure-python reading/writing ``ISO`` disk images (with support
    for ISO 9660 Levels 1, 2 and 3, Joliet and Rock Ridge extensions).
    Requires the `pycdlib <https://pypi.python.org/pypi/pycdlib>`_
    library.


Usage
-----

The ``fs.archive.open_archive`` function is the easiest way to open an
archive filesystem, with an archive located on any other filesystem, directly
determining the class to use from the file extension:

.. code:: python

    >>> from fs import open_fs
    >>> from fs.archive import open_archive

    >>> my_fs = open_fs(u'temp://')
    >>> with open_archive(my_fs, u'test.zip') as archive:
    ...     type(archive)
    <class 'fs.archive.zipfs.ZipFS'>


All the filesystems implemented in ``fs.archive`` also support reading from
— and if not read-only, writing to — a file handle:

.. code:: python

    >>> import fs.archive.tarfs
    >>> with fs.open_fs(u'mem://') as mem:
    ...     with fs.archive.tarfs.TarFS(mem.openbin(u'test.tar', 'w')) as tar:
    ...         tar.setbytes(u'hello', b'Hello, World!')
    ...     with fs.archive.tarfs.TarFS(mem.openbin(u'test.tar', 'r+')) as tar:
    ...         tar.isfile(u'hello')
    True


.. Abstract Base Classes
.. ---------------------
..
.. ``fs.archive`` declares three abstract base classes in ``fs.archive.base``:
..
.. ``ArchiveSaver``
..     defines how an archive is saved (in essence, a class managing
..     the compression of a filesystem).
..
.. ``ArchiveReadFS``
..     a read-only filesystem that implements the methods required
..     to *read* the archive.
..
.. ``ArchiveFS``
..     a `WrapFS` filesystem used to make an archive seemingly writable.


See also
--------

* `fs <https://github.com/Pyfilesystem/pyfilesystem2>`_, the core pyfilesystem2 library
* `fs.sshfs <https://github.com/althonos/fs.sshfs>`_, a SFTP/SSH implementation for
  pyfilesystem2 using `paramiko <https://github.com/paramiko/paramiko>`_
* `fs.smbfs <https://github.com/althonos/fs.smbfs>`_, a SMB implementation for
  pyfilesystem2 using `pysmb <https://github.com/miketeo/pysmb>`_
