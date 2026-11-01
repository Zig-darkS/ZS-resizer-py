# AGENTS.md

## Project Overview
This project is a high-performance CLI Python image resizer powered by FFmpeg.
It relies on modern tooling (`uv`) for fast dependency management and virtual
environment handling.

## Tech Stack & Tooling
- **Language:** Python 3.15.2
- **Media Processing:** FFmpeg (system binary required)
- **Dependency & Package Manager:** `uv` (use `uv pip` instead of standard `pip`)

## Development Guidelines

### 1. Dependency Management
Always use `uv` for managing dependencies. Never use standard `pip`,
`easy_install`, or manual virtual environment creation via `venv` unless
explicitly instructed.

- **Create virtual environment:**
  ```bash
  uv venv
  ```

- **Install project in editable mode:**
  ```bash
  uv pip install -e .
  ```

- **Install dev dependencies:**
  ```bash
  uv pip install pytest
  ```

### 2. Code Style
- Python 3.15.2 syntax. from __future__ import annotations is no longer required for forward references (PEP 649), but may be kept for clarity in modules that still target older interpreters.
- Use frozen `@dataclass(slots=True)` for immutable value objects (see
  `ResizePlan`, `Job`, `Result`).
- Type hints are mandatory on public functions.
- Keep lines under ~100 chars.

### 3. Architecture
- `sizing.py` — pure math. **No I/O, no FFmpeg, no `Path`.** Fully unit-tested.
- `ffmpeg.py` — discovery, capability probing (`probe`), command construction
  (`build_command`, `quality_args`).
- `pipeline.py` — batch orchestration over `Job` → `Result`, catches all
  `ZSResizerError` subclasses.
- `cli.py` — argparse, path collection, human-readable output. **No business
  logic** beyond argument validation.
- `errors.py` — exception hierarchy rooted at `ZSResizerError`.

Never import `ffmpeg` from `sizing`. Never do subprocess calls outside
`ffmpeg.py` / `pipeline.py`.

### 4. Tests
```bash
uv run pytest
```

- New pure logic in `sizing.py` **must** have unit tests in
  `tests/test_sizing.py`.
- `build_command` / `quality_args` tests live in `tests/test_resize.py` and
  must mock `ffmpeg.probe` (don't shell out to a real ffmpeg).
- `run_job` early-return paths (same file / existing dst) are cheap to test
  without ffmpeg installed.

### 5. FFmpeg compatibility
- Target **FFmpeg 8.1.1-full_build**
- Always pass `-hide_banner -loglevel error`.
- Prefer `-frames:v 1 -update 1` for image output so ffmpeg never tries to
  mux a stream.
- `zscale` is optional at build time — always fall back to `scale=…:flags=lanczos`.

### 6. Commits & PRs
- Small, focused commits with descriptive messages.
- Do not commit `_repomix-output.xml`, `.venv/`, `__pycache__/`, `.pytest_cache/`.
