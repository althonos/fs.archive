# from construct import (
#     Struct, Byte, Bytes,
#     Int8un, Const, Enum,
#     Embedded
# )
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

ShortTime = Struct(
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
                              - (this["File Identifier Length"] + 1) % 2,
    )
)

def DirectoryBlock(blocksize):
    return Struct(
        "records" / DirectoryRecord[:],
        "_padding" / Padding(
            lambda ctx: blocksize - sum(r['Record Length'] for r in ctx.records)
        )
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

def _VolumeDescriptor(escape_sequences=None):
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
        "Root Directory Record" / DirectoryRecord,
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
    "PrimaryVolumeDescriptor" / _VolumeDescriptor()

SupplementaryVolumeDescriptor = \
    "SupplementaryVolumeDescriptor" / _VolumeDescriptor(
        "UCS-2 Escape Sequence" / OneOf(
            Bytes(3),
            [b'\x25\x2f\x40', b'\x25\x2f\x43', b'\x25\x2f\x45']
        ),
)



_length = operator.itemgetter("Length")

ComponentRecord = Struct(
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
    "Content" / Bytes(this["Length"] - 2),
)















SystemExtension = Struct(

    "Signature Word" / Bytes(2),

    Embedded(Switch(this['Name'], {

        b'PX': Struct(
            "Length" / Const(Int8un, 44),
            "System Use Entry Version" / Const(Int8un, 1),
            "File Mode" / BothEndian(Int32ul, Int32ub),
            "Links" / BothEndian(Int32ul, Int32ub),
            "User ID" / BothEndian(Int32ul, Int32ub),
            "Group ID" / BothEndian(Int32ul, Int32ub),
            "Serial Number" / BothEndian(Int32ul, Int32ub)
        ),

        b'PN': Struct(
            "Length" / Const(Int8un, 20),
            "System Use Entry Version" / Const(Int8un, 1),
            "Device Number High" / BothEndian(Int32ul, Int32ub),
            "Device Number Low" / BothEndian(Int32ul, Int32ub),
            "Device Number" / Computed(
                this["Device Number High"] << 32 | this["Device Number Low"]),
        ),

        b'SL': Struct(
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
                lambda obj, lst, ctx: sum(map(length, lst)) == _length(obj) - 5,
                ComponentRecord
            ),
        ),

        b'NM': Struct(
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
        ),

        b'CL': Struct(
            "Length" / Const(Int8un, 12),
            "System Use Entry Version" / Const(Int8un, 1),
            "Location of Child Directory" / BothEndian(Int32ul, Int32ub),
        ),

        b'PL': Struct(
            "Length" / Const(Int8un, 12),
            "System Use Entry Version" / Const(Int8un, 1),
            "Location of Parent Directory" / BothEndian(Int32ul, Int32ub),
        ),

        b'RE': Struct(
            "Length" / Const(Int8un, 4),
            "System Use Entry Version" / Const(Int8un, 1),
        ),

        b'TF': Struct(
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
            # "Timestamps" /
            #     IfThenElse(this["Flags"].long_form, LongTime, ShortTime)[
            #         lambda obj: sum(obj["Flags"].values()) - this["Flag"].long_form],

        ),

        b'SF': Struct(
            "Length" / Const(Int8un, 21),
            "System Use Entry Version" / Const(Int8un, 1),
            "Virtual File Size High" / BothEndian(Int32ul, Int32ub),
            "Virtual File Size Low" / BothEndian(Int32ul, Int32ub),
            "Virtual File Size" / Computed(
                this["Virtual File Size High"] << 32 | \
                this["Virtual File Size Low"]
            ),
            "Table Depth" / Int8un,
        ),

    }))

)




# PX = Struct(
#         "Signature Word" / Const(b'PX'),
#         "Length" / Const(Int8un, 44),
#         "System Use Entry Version" / Const(Int8un, 1),
#         "File Mode" / BothEndian(Int32ul, Int32ub),
#         "Links" / BothEndian(Int32ul, Int32ub),
#         "User ID" / BothEndian(Int32ul, Int32ub),
#         "Group ID" / BothEndian(Int32ul, Int32ub),
#         "Serial Number" / BothEndian(Int32ul, Int32ub)
#     )
