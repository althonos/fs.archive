# `fs.archive` [![star me](https://img.shields.io/github/stars/althonos/fs.archive.svg?style=social&maxAge=3600&label=Star)](https://github.com/althonos/fs.archive/stargazers)

[![Source](https://img.shields.io/badge/source-GitHub-303030.svg?logo=git&maxAge=36000&style=flat-square)](https://github.com/althonos/fs.archive)
[![PyPI](https://img.shields.io/pypi/v/fs.archive.svg?logo=pypi&style=flat-square&maxAge=3600)](https://pypi.python.org/pypi/fs.archive)
[![Actions](https://img.shields.io/github/workflow/status/althonos/fs.archive/Test/master?logo=github&style=flat-square&maxAge=300)](https://github.com/althonos/fs.archive/actions)
[![Codecov](https://img.shields.io/codecov/c/github/althonos/fs.archive/master.svg?logo=codecov&style=flat-square&maxAge=300)](https://codecov.io/gh/althonos/fs.archive)
[![Codacy](https://img.shields.io/codacy/grade/eadf418db5a84efd9fa1b470529dcad6/master.svg?logo=codacy&style=flat-square&maxAge=300)](https://www.codacy.com/app/althonos/fs.archive/dashboard)
[![License](https://img.shields.io/pypi/l/fs.archive.svg?style=flat-square&maxAge=36000)](https://choosealicense.com/licenses/mit/)
[![Versions](https://img.shields.io/pypi/pyversions/fs.archive.svg?logo=python&style=flat-square&maxAge=300)](https://pypi.org/project/fs.archive)
[![Format](https://img.shields.io/pypi/format/fs.archive.svg?style=flat-square&maxAge=300)](https://pypi.org/project/fs.archive)
[![GitHub issues](https://img.shields.io/github/issues/althonos/fs.archive.svg?style=flat-square&maxAge=600)](https://github.com/althonos/fs.archive/issues)
[![Downloads](https://img.shields.io/badge/dynamic/json?style=flat-square&color=303f9f&maxAge=86400&label=downloads&query=%24.total_downloads&url=https%3A%2F%2Fapi.pepy.tech%2Fapi%2Fprojects%2Ffs.archive)](https://pepy.tech/project/fs.archive)
[![Changelog](https://img.shields.io/badge/keep%20a-changelog-8A0707.svg?maxAge=2678400&style=flat-square)](https://github.com/althonos/fs.archive/blob/master/CHANGELOG.md)

## Requirements

| **PyFilesystem2** | [![PyPI fs](https://img.shields.io/pypi/v/fs.svg?maxAge=300&style=flat-square)](https://pypi.python.org/pypi/fs) | [![Source fs](https://img.shields.io/badge/source-GitHub-303030.svg?maxAge=36000&style=flat-square)](https://github.com/PyFilesystem/pyfilesystem2) | [![License fs](https://img.shields.io/pypi/l/fs.svg?maxAge=36000&style=flat-square)](https://choosealicense.com/licenses/mit/) |
|:-|:-|:-|:-|
| **six** | [![PyPI six](https://img.shields.io/pypi/v/six.svg?maxAge=300&style=flat-square)](https://pypi.python.org/pypi/six) | [![Source six]( https://img.shields.io/badge/source-GitHub-303030.svg?maxAge=36000&style=flat-square )]( https://github.com/benjaminp/six) | [![License six](https://img.shields.io/pypi/l/six.svg?maxAge=36000&style=flat-square)](https://choosealicense.com/licenses/mit/) |

`fs.archive` supports all Python versions supported by PyFilesystem2:
Python 2.7, and Python 3.5 onwards. Code should still be compatible with
Python 3.4, but is not tested anymore.

## Installation

Install directly from PyPI, using [pip](https://pip.pypa.io/):

```console
$ pip install fs.archive
```

### Additional features

`fs.archive` also provides the following
[extras](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies), allowing you to read from more archive formats:

- **tar.xz**: support for `xz` compressed tar files. Requires the additional
  [`backports.lzma`](https://pypi.python.org/pypi/backports.lzma) module
  in Python 2, but is available natively in Python 3.
- **iso**: pure-python reading/writing ISO disk images (with support for ISO
  9660 Levels 1, 2 and 3, Joliet and Rock Ridge extensions). Requires
  the [`pycdlib`](https://pypi.python.org/pypi/pycdlib) library.
- **7z**: support for 7z archives. Requires the [`py7zr`](https://pypi.python.org/pypi/py7zr)
  and [`iocursor`](https://pypi.python.org/pypi/iocursor) libraries.
- **all**: install all of the above.

## Usage

### Opener

The `fs.archive.open_archive` function is the easiest way to open an
archive filesystem, with an archive located on any other filesystem,
directly determining the class to use from the file extension:

``` python
>>> from fs import open_fs
>>> from fs.archive import open_archive

>>> my_fs = open_fs(u'temp://')
>>> with open_archive(my_fs, u'test.zip') as archive:
...     type(archive)
<class 'fs.archive.zipfs.ZipFS'>
```

### Constructors

All the filesystems implemented in `fs.archive` also support reading
from (and if not read-only, writing to) a file handle:

``` python
>>> import fs.archive.tarfs
>>> with fs.open_fs(u'mem://') as mem:
...     with fs.archive.tarfs.TarFS(mem.openbin(u'test.tar', 'w')) as tar:
...         tar.setbytes(u'hello', b'Hello, World!')
...     with fs.archive.tarfs.TarFS(mem.openbin(u'test.tar', 'r+')) as tar:
...         tar.isfile(u'hello')
True
```

## Feedback

Found a bug ? Have an enhancement request ? Head over to the [GitHub
issue tracker](https://github.com/althonos/fs.archive/issues) of the
project if you need to report or ask something. If you are filling in on
a bug, please include as much information as you can about the issue,
and try to recreate the same bug in a simple, easily reproductible
situation.


## Credits

`fs.sshfs` is developed and maintained by:
- [Martin Larralde](https://github.com/althonos)

The following people contributed to `fs.archive`:
- [Matt Alexander](https://github.com/mattalexx)

This project obviously owes a lot to the PyFilesystem2 project and
[all its contributors](https://github.com/PyFilesystem/pyfilesystem2/blob/master/CONTRIBUTORS.md).


## See also

-   [fs](https://github.com/Pyfilesystem/pyfilesystem2), the core
    pyfilesystem2 library
-   [fs.sshfs](https://github.com/althonos/fs.sshfs), a SFTP/SSH
    implementation for pyfilesystem2 using
    [paramiko](https://github.com/paramiko/paramiko)
-   [fs.smbfs](https://github.com/althonos/fs.smbfs), a SMB
    implementation for pyfilesystem2 using
    [pysmb](https://github.com/miketeo/pysmb)
