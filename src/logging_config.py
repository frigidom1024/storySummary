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
    log_file: str = None,
    enable_file_logging: bool = True,
    log_dir: str = "logs"
) -> logging.Logger:
    """Setup logger with console and optional file output.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Specific log file path (overrides log_dir if provided)
        enable_file_logging: Whether to enable file logging
        log_dir: Directory to store log files
    """
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
    if enable_file_logging:
        if not log_file:
            # Use default log file path
            log_path = Path(log_dir)
            log_path.mkdir(parents=True, exist_ok=True)
            log_file = str(log_path / "story_summary.log")
        else:
            # Ensure log file directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Initialize debug on module import
init_debug()

# Default logger with file storage
logger = setup_logger(
    enable_file_logging=True,
    log_dir="logs"
)
