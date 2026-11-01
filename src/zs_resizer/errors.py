class ZSResizerError(Exception):
    """Base error for the whole project."""


class SizingError(ZSResizerError, ValueError):
    """Invalid dimensions or fit parameters."""


class FFmpegError(ZSResizerError, RuntimeError):
    """FFmpeg/ffprobe not found or failed."""
