# PNG and SVG field guide

A format reference and a dependency-free Python command-line inspector for PNG and SVG files.

## The two conversion jobs

| Question | SVG to PNG | PNG to SVG |
| --- | --- | --- |
| What happens? | Vector shapes are rasterized into pixels. | Pixel regions are traced into approximate vector paths. |
| Good input | Self-contained SVG icons, logos and illustrations. | Sharp logos, icons, line art and simple flat-color graphics. |
| Dimensions | Choose the output pixel width and height before export. | The SVG has a coordinate system (`viewBox`) and a display size. |
| Scaling | Increasing a PNG's display size does not add missing detail. | Paths can scale, but tracing does not recover details absent from the source PNG. |
| Transparency | PNG can store an alpha channel; artwork already drawn as a background remains. | Palette-based tracing may change partially transparent edges. |
| Colors | PNG stores pixels; PNG export is lossless, but rasterization changes the representation. | Reducing the tracing palette merges similar colors and may simplify contours. |
| File size | Depends on pixel dimensions and image content. | Depends on path complexity, precision, colors and metadata. Neither format is always smaller. |
| Photographs | PNG can represent photographs, although another raster format may be more size-efficient. | Automatic tracing usually creates many approximate regions; it is not a faithful editable photo. |
| Embedded bitmaps | Embedded raster content does not become vector detail when rasterized. | An SVG containing only an `<image>` is a bitmap wrapper, not vector tracing. |

## Dimensions and print arithmetic

SVG `width` and `height` describe intrinsic dimensions; `viewBox="min-x min-y width height"` describes coordinates. Percentages need a surrounding viewport, so a standalone file does not always specify a pixel size. This inspector reports unknown values as blank rather than guessing.

For example, an SVG with `width="2in" height="1in"` has CSS intrinsic dimensions of 192 × 96 pixels because CSS uses 96 pixels per inch. A `viewBox="0 0 48 24"` still has a 48 × 24 coordinate space; those are different measurements.

For print, `pixels = inches × target DPI`. A 2-inch square at 300 DPI needs 600 × 600 pixels. This calculation does not add DPI metadata to a file or guarantee printer output quality.

## Batch inspection

Requires Python 3.10 or newer. No packages, accounts or network access are required.

```sh
python inspect_graphics.py ./artwork --recursive > report.csv
python inspect_graphics.py logo.png icon.svg > selected.csv
python -m unittest -v
```

The script processes `.png` and `.svg` files, case-insensitively, in the supplied files or directories. Without `--recursive`, it reads only immediate directory children. It writes CSV to stdout and summaries/errors to stderr; a per-file error produces a row with an `error` field and exit code 1. Usage/path-selection errors use exit code 2. Source files are never rewritten. Symbolic links are skipped.

CSV columns include byte size, intrinsic width/height in CSS pixels where available, `viewBox`, path count, embedded-image count, script count, external-link count, and error text. A viewBox-only SVG gets its coordinate dimensions reported in `view_box`, not silently presented as intrinsic pixels.

PNG inspection reads and validates the signature and IHDR header/CRC; it does **not** decode image data or certify the entire file. SVG inspection parses XML up to 10 MiB, rejects DTD/entity declarations, and reports counts; it does **not** sanitize, render or certify an SVG. CSS resources and inherited styles are not resolved. APNG animation is not inspected. This is an inventory tool, not a converter or a security scanner.

## Browser implementation limits

The associated browser converters process one input at a time and apply these application-defined limits:

| Rule | SVG to PNG | PNG to SVG |
| --- | --- | --- |
| Input bytes | Up to 10 MiB | Up to 10 MiB |
| Pixel limit | Output: at most 16,000,000 pixels and 8,192 px per side | Decoded input: at most 16,000,000 pixels |
| Working resolution | Standard at output size; High at twice each dimension before downsampling | Longest working side at most 1,024 px; smaller details may be lost |
| Output | Lossless PNG; no custom DPI metadata | Traced SVG paths; color limit includes transparency |

These are implementation limits, not limits of the file formats or settings enforced by this inspector.

The browser implementations described here are available at [svgtopix.com](https://svgtopix.com/).

## References

- [W3C SVG sizing](https://www.w3.org/TR/SVG2/coords.html#SizingSVGInCSS)
- [W3C CSS absolute length units](https://www.w3.org/TR/css-values-4/#absolute-lengths)
- [W3C PNG IHDR specification](https://www.w3.org/TR/png-3/#11IHDR)
- [ImageTracer.js tracing and palette options](https://github.com/jankovicsandras/imagetracerjs/blob/master/options.md)

## License

MIT. See LICENSE.
