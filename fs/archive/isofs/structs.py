# coding: utf-8
from __future__ import unicode_literals
from __future__ import division

import pytz
import operator
import datetime
import collections

from construct import *



class BothEndian(Construct):

    def __init__(self, first, last):
        super(BothEndian, self).__init__()
        self.first = first
        self.last = last

    def _parse(self, stream, context, path):
        first_value = self.first.parse_stream(stream)
        last_value = self.last.parse_stream(stream)
        if first_value != last_value:
            raise FieldError("Little- and big-endian values differ.")
        return first_value

    def _build(self, obj, stream, context, path):
        stream.write(self.first.build(obj))
        stream.write(self.last.build(obj))

    def _sizeof(self, context, path):
        return self.first.sizeof(context) + self.last.sizeof(context)


class LongTimeAdapter(Adapter):

    def _decode(self, obj, context):

        if not int(obj['year']):
            return None

        return datetime.datetime(
            int(obj['year']),
            int(obj['month']),
            int(obj['day']),
            int(obj['hour']),
            int(obj['minute']),
            int(obj['second']),
            int(obj['hundredths']) * 10000,
            tzinfo=pytz.FixedOffset(int(obj['gmt_offset'])*15)
        )

    def _encode(self, obj, context):
        if obj is None:
            return {'year': b'0000', 'month': b'00', 'day': b'00', 'hour': b'00',
                    'minute': b'00', 'second': b'00', 'hundredths': b'00',
                    'gmt_offset': 0}

        return {
            'year': '{:>04d}'.format(obj.year).encode('ascii'),
            'month': '{:>02d}'.format(obj.month).encode('ascii'),
            'day': '{:>02d}'.format(obj.day).encode('ascii'),
            'hour': '{:>02d}'.format(obj.hour).encode('ascii'),
            'minute': '{:>02d}'.format(obj.minute).encode('ascii'),
            'second': '{:>02d}'.format(obj.second).encode('ascii'),
            'hundredths': '{:>02d}'.format(obj.microsecond // 10000).encode('ascii'),
            'gmt_offset': int(obj.utcoffset().total_seconds() // 60 // 15),
        }


class ShortTimeAdapter(Adapter):

    def _decode(self, obj, context):

        if not int(obj['month']):
            return None

        return datetime.datetime(
            int(obj['year_offset']) + 1900,
            int(obj['month']),
            int(obj['day']),
            int(obj['hour']),
            int(obj['minute']),
            int(obj['second']),
            tzinfo=pytz.FixedOffset(int(obj['gmt_offset'])*15)
        )

    def _encode(self, obj, context):

        if obj is None:
            return {'year': 0, 'month': 0, 'day': 0, 'hour': 0,
                    'minute': 0, 'second': 0, 'hundredths': 0,
                    'gmt_offset': 0}

        return {
            'year_offset': obj.year - 1900,
            'month': obj.month,
            'day': obj.day,
            'hour': obj.hour,
            'minute': obj.minute,
            'second': obj.second,
            'gmt_offset': int(obj.utcoffset().total_seconds() // 60 // 15),
        }


LongTime = Struct(
    "year"       / Bytes(4),
    "month"      / Bytes(2),
    "day"        / Bytes(2),
    "hour"       / Bytes(2),
    "minute"     / Bytes(2),
    "second"     / Bytes(2),
    "hundredths" / Bytes(2),
    "gmt_offset" / Int8sn,
)
"""`construct.Struct`: Timestamp serialized in 17 bytes.

See Also:
    ISO 9660: 8.4.26.1
"""


ShortTime = Struct(
    "year_offset" / Int8un,
    "month" / Int8un,
    "day" / Int8un,
    "hour" / Int8un,
    "minute" / Int8un,
    "second" / Int8un,
    "gmt_offset" / Int8sn,
)
"""`construct.Struct`: Timestamp serialized in 7 bytes.

See Also:
    ISO 9660: 9.1.5
"""



class SystemExtension(Construct):

    def _parse(self, stream, context, path):
        # read from the stream (usually not directly)
        # return object
        name = Peek(Bytes(2)).parse(stream).decode('ascii')
        return getattr(self, name).parse(stream, context)

    def _build(self, obj, stream, context, path):
        # write obj to the stream (usually not directly)
        # no return value is necessary
        name = obj["Signature Word"]
        stream.write(getattr(self, name).build(obj))

    def _sizeof(self, context, path):
        # return computed size (when fixed size or depends on context)
        # or raise SizeofError if not possible (when variable size)
        raise SizeofError("variable length")

    _length = operator.itemgetter("Length")

    PX = Struct(
        "Signature Word" / Const(b'PX'),
        "Length" / Const(Int8un, 44),
        "System Use Entry Version" / Const(Int8un, 1),
        "File Mode" / BothEndian(Int32ul, Int32ub),
        "Links" / BothEndian(Int32ul, Int32ub),
        "User ID" / BothEndian(Int32ul, Int32ub),
        "Group ID" / BothEndian(Int32ul, Int32ub),
        "Serial Number" / BothEndian(Int32ul, Int32ub)
    )

    PN = Struct(
        "Signature Word" / Const(b'PN'),
        "Length" / Const(Int8un, 20),
        "System Use Entry Version" / Const(Int8un, 1),
        "Device Number High" / BothEndian(Int32ul, Int32ub),
        "Device Number Low" / BothEndian(Int32ul, Int32ub),
        "Device Number" / Computed(
            this["Device Number High"] << 32 | this["Device Number Low"]),
    )

    _ComponentRecord = Struct(
        "Flags" / BitStruct(
            "_7" / Const(Flag, False),
            "_6" / Const(Flag, False),
            "_5" / Flag,
            "_4" / Flag,
            "root" / Flag,
            "parent" / Flag,
            "current" / Flag,
            "continue" / Flag,
        ),
        "Length" / Int8un,
        "Content" / Bytes(_length(this) - 2),
    )

    SL = Struct(
        "Signature Word" / Const('SL'),
        "Length" / Int8un,
        "System Use Entry Version" / Const(Int8un, 1),
        "Flags" / BitStruct(
            '_7' / Const(Flag, False),
            '_6' / Const(Flag, False),
            '_5' / Const(Flag, False),
            '_4' / Const(Flag, False),
            '_3' / Const(Flag, False),
            '_2' / Const(Flag, False),
            '_1' / Const(Flag, False),
            'continue' / Flag,
        ),
        "Component Area" / RepeatUntil(
            lambda obj, lst, ctx: sum(map(_length, lst)) == _length(obj) - 5,
            _ComponentRecord
        )
    )

    NM = Struct(
        "Signature Word" / Const(b'NM'),
        "Length" / Int8un,
        "System Use Entry Version" / Const(Int8un, 1),
        "Flags" / BitStruct(
            "_7" / Const(Flag, False),
            "_6" / Const(Flag, False),
            "_5" / Flag,
            "_4" / Const(Flag, False),
            "_3" / Const(Flag, False),
            "parent" / Flag,
            "current" / Flag,
            "continue" / Flag,
        ),
        "Name Content" / Bytes(_length(this))
    )

    CL = Struct(
        "Signature Word" / Const(b'CL'),
        "Length" / Const(Int8un, 12),
        "System Use Entry Version" / Const(Int8un, 1),
        "Location of Child Directory" / BothEndian(Int32ul, Int32ub),
    )

    PL = Struct(
        "Signature Word" / Const(b'PL'),
        "Length" / Const(Int8un, 12),
        "System Use Entry Version" / Const(Int8un, 1),
        "Location of Parent Directory" / BothEndian(Int32ul, Int32ub),
    )

    RE = Struct(
        "Signature Word" / Const(b'RE'),
        "Length" / Const(Int8un, 4),
        "System Use Entry Version" / Const(Int8un, 1),
    )

    TF = Struct(
        "Signature Word" / Const(b'TF'),
        "Length" / Int8un,
        "System Use Entry Version" / Const(Int8un, 1),
        "Flags" / BitStruct(
            "long_form" / Flag,
            "effective" / Flag,
            "expiration" / Flag,
            "backup" / Flag,
            "attributes" / Flag,
            "access" / Flag,
            "modify" / Flag,
            "creation" / Flag
        ),
        "Timestamps" / IfThenElse(
            this["Flags"].long_form, LongTime, ShortTime)[
            lambda obj: sum(obj["Flags"].values()) - this["Flags"].long_form
        ],
    )

    SF = Struct(
        "Signature Word" / Const(b'SF'),
        "Length" / Const(Int8un, 21),
        "System Use Entry Version" / Const(Int8un, 1),
        "Virtual File Size High" / BothEndian(Int32ul, Int32ub),
        "Virtual File Size Low" / BothEndian(Int32ul, Int32ub),
        "Virtual File Size" / Computed(
            this["Virtual File Size High"] << 32 | \
            this["Virtual File Size Low"]
        ),
        "Table Depth" / Int8un,
    )


def DirectoryRecord(encoding='ascii'):
    return Struct(
        "Record Length"                    / Int8un,
        "Extended Attribute Record Length" / Int8un,
        "Location of Extent"               / BothEndian(Int32ul, Int32ub),
        "Data Length"                      / BothEndian(Int32ul, Int32ub),
        "Recording Date and Time"          / ShortTimeAdapter(ShortTime),
        "Flags" / BitStruct(
            "continue" / Flag,
            "_6" / Const(Flag, False),
            "_5" / Const(Flag, False),
            "has_permissions" / Flag,
            "has_extended_info" / Flag,
            "is_associated" / Flag,
            "is_dir" / Flag,
            "hidden" / Flag,
        ),
        "File Unit Size" / Default(Int8un, 0),
        "Interleave Gap Size" / Default(Byte, b'\x00'),
        "Volume Sequence Number" / BothEndian(Int16ul, Int16ub),
        "File Identifier Length" / Int8un,

        "Raw File Identifier" / Padded(
            ((this["File Identifier Length"]//2)*2)+1,
            Bytes(this["File Identifier Length"]),
            strict=True,
        ),

        "File Identifier" / Computed(
            lambda ctx: (ctx['Raw File Identifier'].decode(encoding)
                         if ctx['Raw File Identifier'] not in (b'\x00', b'\x01')
                         else ctx['Raw File Identifier'].decode('ascii'))
        ),

        "System Extension Length" / Computed(
            this["Record Length"] - 34 - (this["File Identifier Length"]//2)*2
        ),

        "System Extensions" / Padded(
            this["System Extension Length"],
            SystemExtension()[:],
        ),
    )

def DirectoryBlock(blocksize, encoding):
    return Padded(
        lambda ctx: blocksize - sum(r['Record Length'] for r in ctx),
        DirectoryRecord(encoding)[:]
    )

VolumeDescriptorHeader = Struct(
    "type"       / Enum(Byte,
        BootRecord                    = 0,
        PrimaryVolumeDescriptor       = 1,
        SupplementaryVolumeDescriptor = 2,
        VolumePartitionDescriptor     = 3,
        VolumeDescriptorSetTerminator = 255
    ),
    "id" / Const(b'CD001'),
    "version"    / Const(b'\x01'),
)

RawVolumeDescriptor = Struct(
    Embedded(VolumeDescriptorHeader),
    "data"       / Bytes(2041),
)

BootRecord = Struct(
    Embedded(VolumeDescriptorHeader),
    "boot_sys_id" / Bytes(32),
    "boot_id" / Bytes(32),
    "boot_sys_use" / Bytes(1977),
)

def _VolumeDescriptor(encoding, escape_sequences=None):
    return Struct(
        Embedded(VolumeDescriptorHeader),
        Const(b'\x00'),
        "System Identifier" / Bytes(32),
        "Volume Identifier" / Bytes(32),
        Padding(8, b'\x00', strict=True),
        "Volume Space Size" / BothEndian(Int32ul, Int32ub),
        Padded(32, escape_sequences or Pass, b'\x00', strict=True),
        "Volume Set Size" / BothEndian(Int16ul, Int16ub),
        "Volume Sequence Number" / BothEndian(Int16ul, Int16ub),
        "Logical Block Size" / BothEndian(Int16ul, Int16ub),
        "Path Table Size" / BothEndian(Int32ul, Int32ub),
        "Location of Type-L Path Table" / Int32ul,
        "Location of the Optional Type-L Path Table" / Int32ul,
        "Location of Type-M Path Table" / Int32ub,
        "Location of the Optional Type-M Path Table" / Int32ub,
        "Root Directory Record" / DirectoryRecord(encoding),
        "Volume Set Identifier" / Bytes(128),

        # NB: fix for extended publisher info
        "Publisher Identifier" / Default(Bytes(128), b'\x20'*128),
        "Data Preparer Identifier" / Default(Bytes(128), b'\x20'*128),
        "Application Identifier" /   Default(Bytes(128), b'\x20'*128),
        "Copyright File Identifier" / Default(Bytes(38), b'\x20'*38),
        "Abstract File Identifier" / Default(Bytes(36), b'\x20'*36),
        "Bibliographic File Identifier" / Default(Bytes(37), b'\x20'*37),
        "Volume Creation Date and Time" / LongTimeAdapter(LongTime),
        "Volume Modification Date and Time" / LongTimeAdapter(LongTime),
        "Volume Expiration Date and Time" / LongTimeAdapter(LongTime),
        "Volume Effective Date and Time" / LongTimeAdapter(LongTime),

        "File Structure Version" / Const(b'\x01'),
        Padding(1, strict=True),
        "Application Used" / Bytes(512),
        "Reserved" / Bytes(653),
    )

PrimaryVolumeDescriptor = \
    "PrimaryVolumeDescriptor" / _VolumeDescriptor('ascii')

SupplementaryVolumeDescriptor = \
    "SupplementaryVolumeDescriptor" / _VolumeDescriptor(
        'UTF-16BE',
        "UCS-2 Escape Sequences" / OneOf(Bytes(3),
            [b'\x25\x2f\x40', b'\x25\x2f\x43', b'\x25\x2f\x45']
        ),
)
