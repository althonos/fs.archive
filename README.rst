fs.archive
==========

|Source| |PyPI| |Travis| |Codecov| |Codacy| |Format| |License|

.. |Codacy| image:: https://img.shields.io/codacy/grade/eadf418db5a84efd9fa1b470529dcad6/master.svg?style=flat-square&maxAge=300
   :target: https://www.codacy.com/app/althonos/fs.proxy/dashboard

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
| **fs.proxy**      | |PyPI fs.proxy| | |Source fs.proxy| | |License fs.proxy| |
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

.. |License fs.proxy| image:: https://img.shields.io/pypi/l/fs.proxy.svg?maxAge=300&style=flat-square
   :target: https://choosealicense.com/licenses/mit/

.. |Source fs.proxy| image:: https://img.shields.io/badge/source-GitHub-303030.svg?maxAge=300&style=flat-square
   :target: https://github.com/althonos/fs.proxy

.. |PyPI fs.proxy| image:: https://img.shields.io/pypi/v/fs.proxy.svg?maxAge=300&style=flat-square
   :target: https://pypi.python.org/pypi/fs.proxy



Installation
------------

Install directly from PyPI, using `pip <https://pip.pypa.io/>`_ ::

    pip install fs.archive


Usage
-----

The ``fs.archive.open_archive`` context manager is the easiest way to open an
archive filesystem, with an archive located on any other filesystem, determining
from the file extension the type to use :

.. code:: python

    >>> from fs import open_fs
    >>> from fs.archive import open_archive

    >>> my_fs = open_fs(u'temp://')
    >>> with open_archive(my_fs, u'test.zip') as archive:
    ...     type(archive)
    <class 'fs.archive.zipfs.ZipFS'>


All the filesystems implemented in ``fs.archive`` also support reading and
writing from and to a file handle a file handle:

.. code:: python

    >>> import fs.archive.tarfs
    >>> with fs.open_fs(u'mem://') as mem:
    ...     with fs.archive.tarfs.TarFS(mem.openbin(u'test.tar', 'w')) as tar:
    ...         tar.setbytes(u'hello', b'Hello, World!')
    ...     with fs.archive.tarfs.TarFS(mem.openbin(u'test.tar', 'r+')) as tar:
    ...         tar.isfile(u'hello')
    True


``fs.archive`` declares three abstract base classes in ``fs.archive.base``:

* ``ArchiveSaver``: defines how an archive is saved (in essence, a class managing
  the compression of a filesystem)
* ``ArchiveReadFS``: a read-only filesystem that implements the methods required
  to *read* the archive
* ``ArchiveFS``: a `proxy <https://github.com/althonos/fs.proxy>`_ filesystem
  used to make an archive seemingly writable





See also
--------

* `fs <https://github.com/Pyfilesystem/pyfilesystem2>`_, the core pyfilesystem2 library
* `fs.proxy <https://github.com/althonos/fs.proxy>`_, miscellaneous proxy filesystems
  for pyfilesystem2
* `fs.sshfs <https://github.com/althonos/fs.sshfs>`_, a SFTP/SSH implementation for
  pyfilesystem2 using `paramiko <https://github.com/paramiko/paramiko>`_
