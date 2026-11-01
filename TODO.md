# TODO

## Documentation
- [x] Fill [README.md](README.md)
- [x] Fill [AGENTS.md](AGENTS.md)
- [x] Confirm [LICENSE](LICENSE) is MIT

## Testing & CI
- [ ] Add end-to-end CLI test (`tests/test_cli.py`) that runs against a real FFmpeg binary
- [ ] Add GitHub Actions CI (matrix: Python 3.15, FFmpeg 8.1.1 on Linux/Windows)
- [ ] Cover `run_batch` ordering and worker-count logic with tests

## Features
- [ ] Add `--pad-color` (black / white / transparent / hex) for `--fit pad`
- [ ] Add `--resize-canvas` to control the intermediate scaling surface
- [ ] Consider `from __future__ import annotations` removal (PEP 649 is default in 3.15)

## Maintenance
- [ ] Verify AVIF encoder detection against FFmpeg 8.1.1 `full_build`
- [ ] Re-check `quality_args` mappings against current FFmpeg encoder docs
- [ ] Update AGENTS §2 if `from __future__ import annotations` is dropped
