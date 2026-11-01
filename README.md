# ZS-resizer-py

Fast Lanczos image resizer powered by FFmpeg. Resize JPEG, PNG, WebP, AVIF,
TIFF and BMP from the command line with batch processing, multiple fit modes
and parallel workers.

## Requirements

- Python **3.15.2**
- `ffmpeg` and `ffprobe` on `PATH` (or set `--ffmpeg-path` / `FFMPEG_PATH`)
- Optional: FFmpeg built with `zscale` for color-managed Lanczos scaling

Verify installation:

```bash
zs-resizer --doctor
```

## Installation

Uses [`uv`](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -e .
```

Or plain `pip`:

```bash
pip install -e .
```

## Usage

```bash
zs-resizer INPUT [INPUT ...] -w WIDTH [-H HEIGHT] [options]
```

### Examples

```bash
# Single image, width 1920, height follows aspect ratio
zs-resizer photo.jpg -w 1920

# Fit inside 800×800 (no crop, no distortion)
zs-resizer photo.jpg -w 800 -H 800 --fit inside

# Batch: recursive, WebP, suffix to avoid clobbering
zs-resizer ./photos --recursive -w 1920 --output-dir out --suffix _1920

# Exact single output path
zs-resizer in.png -w 1000 -o out/small.png
```

### Fit modes

| Mode | Behavior |
|------|----------|
| `inside` *(default)* | Scale to fit inside the box, preserve aspect ratio |
| `cover` | Scale to cover the box, center-crop the overflow |
| `fill` | Stretch to exact size (distorts aspect ratio) |
| `pad` | Scale to fit, then pad with black to exact size |

### Quality mapping (`-q`, 1..100)

| Output | Encoding |
|--------|----------|
| `.jpg` / `.jpeg` | mapped to `-q:v` (2..31, 100 = best) |
| `.webp` | `-quality` (1..100) |
| `.avif` | mapped to `-crf` (10..63) |
| `.png` | lossless, `-compression_level 9` |

## CLI reference

| Option | Description |
|--------|-------------|
| `-w, --width N` | Target width (px) |
| `-H, --height N` | Target height (px) |
| `--fit MODE` | `inside`, `cover`, `fill`, `pad` |
| `-q, --quality N` | 1..100, higher = better (default `90`) |
| `--engine ENGINE` | `auto`, `zscale`, `swscale` |
| `--strip-metadata` | Drop EXIF / other metadata |
| `--overwrite` | Overwrite existing output |
| `--recursive` | Recurse into subdirectories |
| `-o, --output PATH` | Exact output path (single source only) |
| `--output-dir DIR` | Directory for outputs |
| `--suffix SUFFIX` | Filename suffix, e.g. `_1920` |
| `-j, --jobs N` | Parallel worker processes |
| `--ffmpeg-path PATH` | Explicit FFmpeg binary |
| `--doctor` | Print FFmpeg capabilities and exit |

## Development

```bash
uv run pytest
```

## License

MIT — see [LICENSE](LICENSE)
