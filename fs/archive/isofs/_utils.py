# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import string

from ...path import split, join



def iso_name_slugify(name):
    """Slugify a name in the ISO-9660 way.

    Example:
        >>> slugify('épatant')
        "_patant"
    """
    name = name.encode('ascii', 'replace').replace(b'?', b'_')
    return name.decode('ascii')


def iso_name_increment(name, is_dir=False, max_length=8):
    """Increment an ISO name to avoid name collision.

    Example:
        >>> iso_name_increment('foo.txt')
        'foo1.txt'
        >>> iso_name_increment('bar10')
        'bar11'
        >>> iso_name_increment('bar99', max_length=5)
        'ba100'
    """
    # Split the extension if needed
    if not is_dir and '.' in name:
        name, ext = name.rsplit('.')
        ext = '.{}'.format(ext)
    else:
        ext = ''

    # Find the position of the last letter
    for position, char in reversed(list(enumerate(name))):
        if char not in string.digits:
            break

    # Extract the numbers and the text from the name
    base, tag = name[:position+1], name[position+1:]
    tag = str(int(tag or 0) + 1)

    # Crop the text if the numbers are too long
    if len(tag) + len(base) > max_length:
        base = base[:max_length - len(tag)]

    # Return the name with the extension
    return ''.join([base, tag, ext])


def iso_path_slugify(path, path_table, is_dir=False, strict=True):
    """Slugify a path, maintaining a map with the previously slugified paths.

    The path table is used to prevent slugified names from collisioning,
    using the `iso_name_increment` function to deduplicate slugs.

    Example:
        >>> path_table = {'/': '/'}
        >>> iso_path_slugify('/ébc.txt', path_table)
        '/_BC.TXT'
        >>> iso_path_slugify('/àbc.txt', path_table)
        '/_BC2.TXT'
    """
    # Split the path to extract the parent and basename
    parent, base = split(path)

    # Get the parent in slugified form
    slug_parent = path_table[parent]

    # Slugify the base name
    if is_dir:
        slug_base = iso_name_slugify(base)[:8]
    else:
        name, ext = base.rsplit('.', 1) if '.' in base else (base, '')
        slug_base = '.'.join([iso_name_slugify(name)[:8], ext])
    if strict:
        slug_base = slug_base.upper()

    # Deduplicate slug if needed and update path_table
    slugs = set(path_table.values())
    path_table[path] = slug = join(slug_parent, slug_base)
    while slug in slugs:
        slug_base = iso_name_increment(slug_base, is_dir)
        path_table[path] = slug = join(slug_parent, slug_base)

    # Return the unique slug
    return slug
