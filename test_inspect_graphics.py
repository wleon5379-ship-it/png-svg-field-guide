import contextlib
import csv
import io
from pathlib import Path
import struct
import tempfile
import unittest
import zlib
from inspect_graphics import inspect, main


def png_bytes(width, height):
    def chunk(kind, payload):
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xffffffff)
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    pixels = b''.join(b'\0' + b'\xff\0\0\xff' * width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')


class InspectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def write(self, name, data):
        path = self.root / name; path.write_bytes(data); return path
    def test_png_and_invalid_crc(self):
        path = self.write('tiny.png', png_bytes(3, 2))
        self.assertEqual((inspect(path)['width_px'], inspect(path)['height_px']), (3, 2))
        bad = bytearray(path.read_bytes()); bad[29] ^= 1; path.write_bytes(bad)
        self.assertIn('CRC', inspect(path)['error'])
    def test_svg_units_and_bitmap_wrapper(self):
        path = self.write('icon.svg', b'<svg xmlns="http://www.w3.org/2000/svg" width="2in" height="1in" viewBox="0 0 48 24"><path d="M0 0L2 2"/><image href="data:image/png;base64,AA=="/></svg>')
        row = inspect(path)
        self.assertEqual((row['width_px'], row['height_px'], row['paths'], row['images']), (192, 96, 1, 1))
    def test_viewbox_is_not_guessed_pixels(self):
        path = self.write('view.svg', b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 20"/>')
        self.assertEqual(inspect(path)['width_px'], '')
        self.assertEqual(inspect(path)['view_box'], '0 0 50 20')
    def test_dtd_rejected(self):
        path = self.write('bad.svg', b'<!DOCTYPE svg [<!ENTITY foo "hello">]><svg xmlns="http://www.w3.org/2000/svg"/>')
        self.assertIn('DTD', inspect(path)['error'])
    def test_batch_recursive_csv_and_error_exit(self):
        self.write('good.png', png_bytes(2, 1)); self.write('broken.png', b'bad')
        (self.root / 'nested').mkdir(); (self.root / 'nested' / 'more.PNG').write_bytes(png_bytes(1, 1))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): code = main([str(self.root), '--recursive'])
        rows = list(csv.DictReader(io.StringIO(out.getvalue())))
        self.assertEqual((code, len(rows)), (1, 3)); self.assertEqual(sum(bool(r['error']) for r in rows), 1)


if __name__ == '__main__': unittest.main()
