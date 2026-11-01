# AGENTS.md

## Project Overview
This project is a high-performance CLI Python image resizer powered by FFmpeg. It relies on modern tooling (`uv`) for fast dependency management and virtual environment handling.

---

## Tech Stack & Tooling
- **Language:** Python 3.15.2
- **Media Processing:** FFmpeg (system binary required)
- **Dependency & Package Manager:** `uv` (use `uv pip` instead of standard `pip`)

---

## Development Guidelines

### 1. Dependency Management
Always use `uv` for managing dependencies. Never use standard `pip`, `easy_install`, or manual virtual environment creation via `venv` unless explicitly instructed.

- **Create virtual environment:**
  ```bash
  uv venv
