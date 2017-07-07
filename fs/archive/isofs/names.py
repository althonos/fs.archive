
import re
import operator
import collections


def get_iso_name(record, clean=True):
    rx = re.compile(r'\.?;\d$') if clean else None
    name = record.file_identifier().decode('ascii').lower()
    return rx.sub('', name) if clean else name

def get_rridge_name(record):
    return record.rock_ridge.name().decode('utf-8')

def get_joliet_name(record):
    name = record.file_identifier()
    encoding = 'ascii' if name in (b'.', b'..') else 'utf-16-be'
    return name.decode(encoding)




def iso_escape(name):
    """Unicode to str with iso escaping.
    """

    binary_name = bytearray(name.encode('utf-8'))
    for index, char in enumerate(binary_name):
        if char > 127:
            binary_name[index] = ord(b'_')
    return bytes(binary_name).decode('ascii')
