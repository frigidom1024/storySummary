import logging
import os
import sys
from pathlib import Path


# Module debug levels: DEBUG=analyzer,books,websocket
_DEBUG_MODULES: set = set()
_ENABLED = False

_loggers = {}  # Cache for module-specific loggers


def init_debug():
    """Initialize debug modules from environment variable."""
    global _DEBUG_MODULES, _ENABLED
    debug_env = os.environ.get('DEBUG', '')
    if debug_env:
        _DEBUG_MODULES = set(m.strip() for m in debug_env.split(',') if m.strip())
        _ENABLED = True
        print(f"[DEBUG] Enabled modules: {_DEBUG_MODULES}", file=sys.stderr)
    else:
        _ENABLED = False


def _get_module_logger(module: str) -> logging.Logger:
    """Get or create a logger for a specific module."""
    if module not in _loggers:
        logger = logging.getLogger(module)
        logger.setLevel(logging.DEBUG)
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(f"【{module}】：%(message)s"))
            logger.addHandler(handler)
        _loggers[module] = logger
    return _loggers[module]


def debug(module: str, message: str, *args, **kwargs):
    """Print debug message for a module with 【module】：message format.

    Usage:
        debug("analyzer", "Starting analysis for book {}", book_id)
        debug("books", "Request received for book_id={}", book_id)

    Environment variable DEBUG controls which modules are shown:
        DEBUG=analyzer,books    # Only show analyzer and books modules
        DEBUG=all                # Show all debug messages
        DEBUG=                    # Disable all debug (default)
    """
    if not _ENABLED:
        return

    if 'all' in _DEBUG_MODULES or module in _DEBUG_MODULES:
        msg = message.format(*args, **kwargs) if (args or kwargs) else message
        logger = _get_module_logger(module)
        logger.debug(msg)


def setup_logger(
    name: str = "story-summary",
    level: int = logging.INFO,
    log_file: str = None
) -> logging.Logger:
    """Setup logger with console and optional file output."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Initialize debug on module import
init_debug()

# Default logger
logger = setup_logger()
