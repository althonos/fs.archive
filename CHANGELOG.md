# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).


## [Unreleased]

[Unreleased]: https://github.com/althonos/fs.archive/compare/v0.7.1...HEAD


## [v0.7.1] - 2021-12-24

[v0.7.1]: https://github.com/althonos/fs.archive/compare/v0.7.0...v0.7.1

### Fixed
- `fs.archive.open_archive` not being able to open 7z files ([#8](https://github.com/althonos/fs.archive/issues/8)).
- `py7zr.exceptions.Bad7zFile` not being wrapped when thrown in `SevenZipReadFS.__init__`.


## [v0.7.0] - 2021-12-14

[v0.7.0]: https://github.com/althonos/fs.archive/compare/v0.6.2...v0.7.0

### Added
- This changelog file.
- `7z` extra for reading and writing 7z archives with the `fs.archive.sevenzipfs` module.

### Fixed
- Abstract base classes for collection types being removed from the `collections` module in Python 3.10.
- Handling of Rock Ridge entries in new `pycdlib` versions.
- Namespace handling in `ZipReadFS.scandir` causing `getinfo` to be called when not needed.

### Changed
- Use `fs.path.isbase` in `ZipReadFS` to check for implicit directories.
- Use the stdlib implementation of `TarFile.xzopen` on Python 3.


## [v0.6.2] - 2019-02-22

[v0.6.2]: https://github.com/althonos/fs.archive/compare/v0.6.1...v0.6.2

### Changed
- Allow all versions of `fs` greater than `v2.2` to work.


## [v0.6.1] - 2019-02-11

[v0.6.1]: https://github.com/althonos/fs.archive/compare/v0.6.0...v0.6.1

### Changed
- Bump required `fs` version to `v2.3.0`


## [v0.6.0] - 2019-01-06

[v0.6.0]: https://github.com/althonos/fs.archive/compare/v0.5.0...v0.6.0

### Changed
- Bump required `fs` version to `v2.2.0`


## [v0.5.0] - 2018-08-13

[v0.5.0]: https://github.com/althonos/fs.archive/compare/v0.4.1...v0.5.0

### Changed
- Bump required `fs` version to `v2.1.0`


## [v0.4.1] - 2018-08-07

[v0.4.1]: https://github.com/althonos/fs.archive/compare/v0.4.0...v0.4.1

### Fixed
- Change of behaviour in `zipfile` since Python 3.7.
- `typing.GenericMeta` removed in Python 3.7.

### Changed
- Bump optional `pycdlib` minimum version to `1.4`.


## [v0.4.0] - 2018-07-12

[v0.4.0]: https://github.com/althonos/fs.archive/compare/v0.3.2...v0.4.0

### Changed
- Drop support of Python 3.3.
- Pin optional `pycdlib` minimum version to `1.3` to avoid `weakref` issues in later versions.

### Fixed
- Encoding issues with the `TarFS` opener.
- `TarFS` checking for member existence more than required is `listdir` or `exists`.


## [v0.3.2] - 2018-04-16

[v0.3.2]: https://github.com/althonos/fs.archive/compare/v0.3.1...v0.3.2

### Fixed
- Typo in Python 2 code of `TarSaver`.
- Potential bug with mix of inferred and explicit directories in `TarReadFS`.
- `NoWrapMeta` not working with new typed `WrapFS` metaclass.

### Changed
- Avoid using private API parts of `pycdlib`.


## [v0.3.1] - 2018-03-10

[v0.3.1]: https://github.com/althonos/fs.archive/compare/v0.3.0...v0.3.1

### Fixed
- `ArchiveFS` not closing the wrapped filesystem.


## [v0.3.0] - 2018-02-20

[v0.3.0]: https://github.com/althonos/fs.archive/compare/v0.2.0...v0.3.0

### Removed
- `fs.proxy` dependency.

### Fixed
- Metadata not being copied with files in `WrapWritable`.
- `TarFS.extractfile` returning an incomplete file-like object.

### Changed
- Properly implement `WrapWritable.scandir` instead of relying on `listdir` and `getinfo`.
- Bump optional `pycdlib` minimum version to `1.3`.


## [v0.2.0] - 2017-08-29

[v0.2.0]: https://github.com/althonos/fs.archive/compare/v0.1.0...v0.2.0

### Added
- `iso` extra for reading and writing ISO disk images with the `fs.archive.isofs` module.

### Fixed
- `fs.opener.errors` changing name in `fs` version `2.0.7`.
- `Info` properties requiring some namespaces since `fs` version `2.0.8`.

### Changed
- Make `open_archive` yield read-only filesystems if the source is read-only.


## [v0.1.0] - 2017-07-03

[v0.1.0]: https://github.com/althonos/fs.archive/compare/b73357aa...v0.1.0

Initial release.
