
# Configuration of logging module
LOGGING_DIC = {
    "version": 1.0,
    "disable_existing_loggers": False,
    # Format of logging
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(threadName)s:%(thread)d [%(name)s] %(levelname)s [%(pathname)s:% (lineno)d] %(message)s",
            "datefmt": "[%d-%m-%Y] [%H:%M:%S]"
        },
        "simple": {
            "format": "%(asctime)s [%(name)s] %(levelname)s %(message)s",
            "datefmt": "[%d-%m-%Y] [%H:%M:%S]"
        },
        "test": {
            "format": "%(asctime)s %(message)s",
            "datefmt": "[%d-%m-%Y] [%H:%M:%S]"
        }
    },
    "filters": {

    },
    
    # Log handlers
    "handlers": {
        "console_debug_handler": {
            "level": "DEBUG",                    # Handled level limited
            "class": "logging.StreamHandler",    # Output to console
            "formatter": "simple"                # Log format
        },
        "file_info_handler": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",  # Save to file, logs rotating
            "filename": "./logs/user_info.log",
            "maxBytes": 1024*1024*10,                         # Maximum size of logging file: 10MB
            "backupCount": 10,                                # Maximum numbers of log files
            "encoding": "utf-8",
            "formatter": "standard"
        },
        "file_debug_handler": {
            "level": "DEBUG",
            "class": "logging.FileHandler",      # Save loggings to file
            "filename": "./logs/user_debug.log",        # Path of log files
            "encoding": "utf-8",
            "formatter": "test"
        }
    },
    
    # Logs recorders
    "loggers": {
        # app_name used when logging.getLogger imported
        "logger1": {
            # Handler assigned to log file
            "handlers": ["console_debug_handler"],
            # Level limitation of log recording
            "level": "DEBUG",
            # Default as True: propagate to higher levels of loggers
            "propagate": False
        },
        "logger2": {
            "handlers": ["console_debug_handler", "file_debug_handler"],
            "level": "INFO",
            "propagate": False
        },
        "logger3": {
            "handlers": ["file_debug_handler"],
            "level": "INFO",
            "propagate": False
        },
    }
    
}
