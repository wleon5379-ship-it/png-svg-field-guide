#!/usr/bin/env python3
"""Read PNG headers and SVG structure; write a batch CSV without changing files."""
import argparse
import csv
import math
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

FIELDS = ['file', 'format', 'bytes', 'width_px', 'height_px', 'view_box',
          'paths', 'images', 'scripts', 'external_links', 'error']
SVG_NS = 'http://www.w3.org/2000/svg'
UNIT = {'': 1, 'px': 1, 'in': 96, 'cm': 96 / 2.54, 'mm': 96 / 25.4,
        'q': 96 / 101.6, 'pt': 96 / 72, 'pc': 16}


def length_px(text):
    match = re.fullmatch(r'\s*(\d*\.?\d+(?:[eE][+-]?\d+)?)\s*([a-z]*)\s*', text or '', re.I)
    if not match or match[2].lower() not in UNIT:
        return ''
    value = float(match[1]) * UNIT[match[2].lower()]
    return round(value, 6) if math.isfinite(value) and value > 0 else ''


def png_info(path):
    with path.open('rb') as stream:
        head = stream.read(33)
    if len(head) != 33 or head[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Invalid or truncated PNG header')
    size, kind = struct.unpack('>I4s', head[8:16])
    if size != 13 or kind != b'IHDR':
        raise ValueError('Expected a 13-byte IHDR as the first PNG chunk')
    if zlib.crc32(head[12:29]) & 0xffffffff != struct.unpack('>I', head[29:33])[0]:
        raise ValueError('PNG IHDR CRC mismatch')
    width, height = struct.unpack('>II', head[16:24])
    if not 0 < width <= 0x7fffffff or not 0 < height <= 0x7fffffff:
        raise ValueError('Invalid PNG dimensions')
    return {'width_px': width, 'height_px': height}


def svg_info(path):
    with path.open('rb') as stream:
        data = stream.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('SVG exceeds inspector XML limit of 10 MiB')
    # Removing NULs makes UTF-16/32 declarations visible to this rejection check.
    if re.search(br'<!\s*(?:DOCTYPE|ENTITY)', data.replace(b'\0', b''), re.I):
        raise ValueError('DTD and entity declarations are not supported')
    root = ET.fromstring(data)
    if root.tag != '{' + SVG_NS + '}svg':
        raise ValueError('Expected an SVG root in the SVG namespace')
    paths = images = scripts = external = 0
    for element in root.iter():
        if element.tag == '{' + SVG_NS + '}path': paths += 1
        if element.tag == '{' + SVG_NS + '}image': images += 1
        if element.tag == '{' + SVG_NS + '}script': scripts += 1
        for key, value in element.attrib.items():
            if key in ('href', '{http://www.w3.org/1999/xlink}href'):
                ref = value.strip()
                if ref and not ref.startswith(('#', 'data:')): external += 1
    return {'width_px': length_px(root.get('width')),
            'height_px': length_px(root.get('height')),
            'view_box': root.get('viewBox', ''), 'paths': paths, 'images': images,
            'scripts': scripts, 'external_links': external}


def inspect(path):
    row = dict.fromkeys(FIELDS, '')
    row.update(file=str(path), format=path.suffix.lower()[1:])
    try:
        row['bytes'] = path.stat().st_size
        row.update(png_info(path) if path.suffix.lower() == '.png' else svg_info(path))
    except (OSError, ValueError, ET.ParseError, OverflowError) as error:
        row['error'] = str(error)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', type=Path, nargs='+')
    parser.add_argument('--recursive', action='store_true')
    args = parser.parse_args(argv)
    selected = {}
    for target in args.paths:
        if target.is_symlink():
            continue
        if not target.exists(): parser.error(f'Path does not exist: {target}')
        candidates = (target.rglob('*') if args.recursive else target.iterdir()) if target.is_dir() else [target]
        for item in candidates:
            if item.is_file() and not item.is_symlink() and item.suffix.lower() in ('.png', '.svg'):
                selected[str(item.resolve())] = item
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS, lineterminator='\n')
    writer.writeheader()
    errors = 0
    for key in sorted(selected):
        row = inspect(selected[key]); writer.writerow(row)
        if row['error']:
            errors += 1
            print(f"{row['file']}: {row['error']}", file=sys.stderr)
    print(f'Inspected {len(selected)} file(s); {errors} error(s).', file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
