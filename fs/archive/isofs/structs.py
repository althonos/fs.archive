# from construct import (
#     Struct, Byte, Bytes,
#     Int8un, Const, Enum,
#     Embedded
# )
from __future__ import unicode_literals
from __future__ import division

import pytz
import datetime

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


class DescDateTimeAdapter(Adapter):

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
            tzinfo = pytz.FixedOffset(int(obj['gmt_offset'])*15)
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
            'gmt_offset': int(obj.utcoffset().total_seconds() // 60),
        }


class DirDateTimeAdapter(Adapter):

    def _decode(self, obj, context):
        return datetime.datetime(
            int(obj['year_offset']) + 1900,
            int(obj['month']),
            int(obj['day']),
            int(obj['hour']),
            int(obj['minute']),
            int(obj['second']),
            tzinfo = pytz.FixedOffset(int(obj['gmt_offset'])*15)
        )

    def _encode(self, obj, context):
        return {
            'year_offset': obj.year - 1900,
            'month': obj.month,
            'day': obj.day,
            'hour': obj.hour,
            'minute': obj.minute,
            'second': obj.second,
            'gmt_offset': int(obj.utcoffset().total_seconds() // 60),
        }


DescDateTime = Struct(
    "year"       / Bytes(4),
    "month"      / Bytes(2),
    "day"        / Bytes(2),
    "hour"       / Bytes(2),
    "minute"     / Bytes(2),
    "second"     / Bytes(2),
    "hundredths" / Bytes(2),
    "gmt_offset" / Int8sn,
)

DirDateTime = Struct(
    "year_offset" / Int8un,
    "month" / Int8un,
    "day" / Int8un,
    "hour" / Int8un,
    "minute" / Int8un,
    "second" / Int8un,
    "gmt_offset" / Int8sn,
)

DirectoryRecord = Struct(
    "Record Length"                    / Int8un,
    "Extended Attribute Record Length" / Int8un,
    "Location of Extent"               / BothEndian(Int32ul, Int32ub),
    "Data Length"                      / BothEndian(Int32ul, Int32ub),
    "Recording Date and Time"          / DirDateTimeAdapter(DirDateTime),
    "Flags" / BitStruct(
        "is_not_last" / Flag,
        "_r2" / Default(Flag, False),
        "_r1" / Default(Flag, False),
        "has_permissions" / Flag,
        "has_extended_info" / Flag,
        "is_associated" / Flag,
        "is_dir" / Flag,
        "hidden" / Flag,
    ),
    "File Unit Size" / Default(Int8un, 0),
    "_Interleave gap" / Default(Byte, b'\x00'),
    "Volume Sequence Number" / BothEndian(Int16ul, Int16ub),
    "File Identifier Length" / Int8un,

    "File Identifier" / Bytes(this["File Identifier Length"]),

    "_Padding" / If(
        this["File Identifier Length"] % 2 == 0,
        Padding(1, b'\0', strict=True),
    ),

    "System Use" / Bytes(
        this["Record Length"] - 33 - this["File Identifier Length"] \
                              - (this["File Identifier Length"]+1) % 2
    )
)


def DirectoryBlock(blocksize):
    return Struct(
        "records" / DirectoryRecord[:],
        "_padding" / Padding(
            lambda ctx: blocksize - sum(r['Record Length'] for r in ctx.records)
        )
    )


VolumeDescriptor = Struct(
    "type"       / Enum(Byte,
        BootRecord                    = 0,
        PrimaryVolumeDescriptor       = 1,
        SupplementaryVolumeDescriptor = 2,
        VolumeDescriptorSetTerminator = 255
    ),
    "id" / Const(b'CD001'),
    "version"    / Const(b'\x01'),
)

RawVolumeDescriptor = Struct(
    Embedded(VolumeDescriptor),
    "data"       / Bytes(2014),
)

BootRecord = Struct(
    Embedded(VolumeDescriptor),
    "boot_sys_id" / Bytes(32),
    "boot_id" / Bytes(32),
    "boot_sys_use" / Bytes(1977),
)

PrimaryVolumeDescriptor = Struct(
    Embedded(VolumeDescriptor),
    Const(b'\x00'),
    "System Identifier" / Bytes(32),
    "Volume Identifier" / Bytes(32),
    Padding(8, b'\x00', strict=True),
    "Volume Space Size" / BothEndian(Int32ul, Int32ub),
    Padding(32, b'\x00', strict=True),
    "Volume Set Size" / BothEndian(Int16ul, Int16ub),
    "Volume Sequence Number" / BothEndian(Int16ul, Int16ub),
    "Logical Block Size" / BothEndian(Int16ul, Int16ub),
    "Path Table Size" / BothEndian(Int32ul, Int32ub),
    "Location of Type-L Path Table" / Int32ul,
    "Location of the Optional Type-L Path Table" / Int32ul,
    "Location of Type-M Path Table" / Int32ub,
    "Location of the Optional Type-M Path Table" / Int32ub,
    "Root Directory Record" / DirectoryRecord,
    "Volume Set Identifier" / Bytes(128),

    # NB: fix for extended publisher info
    "Publisher Identifier" / Default(Bytes(128), b'\x20'*128),
    "Data Preparer Identifier" / Default(Bytes(128), b'\x20'*128),
    "Application Identifier" /   Default(Bytes(128), b'\x20'*128),
    "Copyright File Identifier" / Default(Bytes(38), b'\x20'*38),
    "Abstract File Identifier" / Default(Bytes(36), b'\x20'*36),
    "Bibliographic File Identifier" / Default(Bytes(37), b'\x20'*37),
    "Volume Creation Date and Time" / DescDateTimeAdapter(DescDateTime),
    "Volume Modification Date and Time" / DescDateTimeAdapter(DescDateTime),
    "Volume Expiration Date and Time" / DescDateTimeAdapter(DescDateTime),
    "Volume Effective Date and Time" / DescDateTimeAdapter(DescDateTime),

    "File Structure Version" / Const(b'\x01'),
    Padding(1, strict=True),
    "Application Used" / Bytes(512),
    "Reserved" / Bytes(653),
)

VolumeDescriptorParser = Union(
    "VolumeDescriptor" / VolumeDescriptor,
    "PrimaryVolumeDescriptor" / Optional(PrimaryVolumeDescriptor),
    "BootRecord" / Optional(BootRecord),
    "RawVolumeDescriptor" / Optional(RawVolumeDescriptor),
)
