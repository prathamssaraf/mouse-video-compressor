import logging
import logging.handlers
import os
import sys
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogComponent(str, Enum):
    MOTION_DETECTION = "motion_detection"
    COMPRESSION = "compression"
    FILE_HANDLER = "file_handler"
    API = "api"
    PROGRESS_TRACKER = "progress_tracker"
    DATABASE = "database"
    WEBSOCKET = "websocket"
    SYSTEM = "system"


@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    component: LogComponent
    message: str
    job_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    exception_info: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class CompressorLogger:
    """
    Centralized logging system for the video compressor application
    """
    
    def __init__(self, 
                 log_dir: str = "./logs",
                 app_name: str = "mouse_video_compressor",
                 max_file_size_mb: int = 10,
                 backup_count: int = 5,
                 console_level: LogLevel = LogLevel.INFO,
                 file_level: LogLevel = LogLevel.DEBUG,
                 json_logging: bool = True):
        
        self.log_dir = Path(log_dir)
        self.app_name = app_name
        self.json_logging = json_logging
        
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up logging configuration
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set up file handler with rotation
        log_file = self.log_dir / f"{app_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, file_level.value))
        
        # Set up console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, console_level.value))
        
        # Set up formatters
        if json_logging:
            file_formatter = JsonFormatter()
            console_formatter = ColoredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_formatter = formatter
            console_formatter = formatter
        
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Set up component-specific loggers
        self.component_loggers = {}
        for component in LogComponent:
            component_logger = logging.getLogger(f"{app_name}.{component.value}")
            component_logger.setLevel(logging.DEBUG)
            self.component_loggers[component] = component_logger
        
        # Async logging support
        self._log_queue = queue.Queue()
        self._log_worker = None
        self._async_logging = False
        
        # Performance tracking
        self.log_stats = {
            'total_logs': 0,
            'logs_by_level': {level.value: 0 for level in LogLevel},
            'logs_by_component': {comp.value: 0 for comp in LogComponent},
            'errors_count': 0,
            'last_error': None
        }
        
        self._stats_lock = threading.Lock()
    
    def start_async_logging(self):
        """Start asynchronous logging worker thread"""
        if not self._async_logging:
            self._async_logging = True
            self._log_worker = threading.Thread(target=self._log_worker_thread, daemon=True)
            self._log_worker.start()
    
    def stop_async_logging(self):
        """Stop asynchronous logging worker thread"""
        if self._async_logging:
            self._async_logging = False
            # Process remaining logs
            while not self._log_queue.empty():
                try:
                    log_entry = self._log_queue.get_nowait()
                    self._write_log_entry(log_entry)
                except queue.Empty:
                    break
    
    def _log_worker_thread(self):
        """Background worker for asynchronous logging"""
        while self._async_logging:
            try:
                log_entry = self._log_queue.get(timeout=1.0)
                self._write_log_entry(log_entry)
                self._log_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                # Fallback to direct logging for critical errors
                self.logger.error(f"Error in log worker thread: {e}")
    
    def _write_log_entry(self, entry: LogEntry):
        """Write a log entry to the appropriate logger"""
        logger = self.component_loggers.get(entry.component, self.logger)
        
        # Prepare log message
        message = entry.message
        extra = {
            'job_id': entry.job_id,
            'user_id': entry.user_id,
            'request_id': entry.request_id,
            'component': entry.component.value,
            'timestamp': entry.timestamp.isoformat()
        }
        
        if entry.extra_data:
            extra.update(entry.extra_data)
        
        # Log based on level
        log_level = getattr(logging, entry.level.value)
        logger.log(log_level, message, extra=extra, exc_info=entry.exception_info)
        
        # Update statistics
        with self._stats_lock:
            self.log_stats['total_logs'] += 1
            self.log_stats['logs_by_level'][entry.level.value] += 1
            self.log_stats['logs_by_component'][entry.component.value] += 1
            
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                self.log_stats['errors_count'] += 1
                self.log_stats['last_error'] = entry.timestamp.isoformat()
    
    def _log(self, level: LogLevel, component: LogComponent, message: str,
             job_id: Optional[str] = None, user_id: Optional[str] = None,
             request_id: Optional[str] = None, extra_data: Optional[Dict[str, Any]] = None,
             exception: Optional[Exception] = None):
        """Internal logging method"""
        
        # Prepare exception info
        exception_info = None
        if exception:
            exception_info = ''.join(traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ))
        
        log_entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            component=component,
            message=message,
            job_id=job_id,
            user_id=user_id,
            request_id=request_id,
            extra_data=extra_data,
            exception_info=exception_info
        )
        
        if self._async_logging:
            self._log_queue.put(log_entry)
        else:
            self._write_log_entry(log_entry)
    
    # Convenience methods for different components
    def log_motion_detection(self, level: LogLevel, message: str, **kwargs):
        """Log motion detection events"""
        self._log(level, LogComponent.MOTION_DETECTION, message, **kwargs)
    
    def log_compression(self, level: LogLevel, message: str, **kwargs):
        """Log compression events"""
        self._log(level, LogComponent.COMPRESSION, message, **kwargs)
    
    def log_file_operation(self, level: LogLevel, message: str, **kwargs):
        """Log file operations"""
        self._log(level, LogComponent.FILE_HANDLER, message, **kwargs)
    
    def log_api_request(self, level: LogLevel, message: str, **kwargs):
        """Log API requests"""
        self._log(level, LogComponent.API, message, **kwargs)
    
    def log_progress(self, level: LogLevel, message: str, **kwargs):
        """Log progress tracking events"""
        self._log(level, LogComponent.PROGRESS_TRACKER, message, **kwargs)
    
    def log_database(self, level: LogLevel, message: str, **kwargs):
        """Log database operations"""
        self._log(level, LogComponent.DATABASE, message, **kwargs)
    
    def log_websocket(self, level: LogLevel, message: str, **kwargs):
        """Log WebSocket events"""
        self._log(level, LogComponent.WEBSOCKET, message, **kwargs)
    
    def log_system(self, level: LogLevel, message: str, **kwargs):
        """Log system events"""
        self._log(level, LogComponent.SYSTEM, message, **kwargs)
    
    # Convenience methods for different log levels
    def debug(self, component: LogComponent, message: str, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, component, message, **kwargs)
    
    def info(self, component: LogComponent, message: str, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, component, message, **kwargs)
    
    def warning(self, component: LogComponent, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, component, message, **kwargs)
    
    def error(self, component: LogComponent, message: str, **kwargs):
        """Log error message"""
        self._log(LogLevel.ERROR, component, message, **kwargs)
    
    def critical(self, component: LogComponent, message: str, **kwargs):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, component, message, **kwargs)
    
    # Job-specific logging methods
    def log_job_started(self, job_id: str, job_type: str, **kwargs):
        """Log job start"""
        self.info(LogComponent.SYSTEM, f"Job started: {job_type}", 
                 job_id=job_id, extra_data={'job_type': job_type}, **kwargs)
    
    def log_job_completed(self, job_id: str, duration: float, **kwargs):
        """Log job completion"""
        self.info(LogComponent.SYSTEM, f"Job completed in {duration:.2f}s", 
                 job_id=job_id, extra_data={'duration': duration}, **kwargs)
    
    def log_job_failed(self, job_id: str, error: Exception, **kwargs):
        """Log job failure"""
        self.error(LogComponent.SYSTEM, f"Job failed: {str(error)}", 
                  job_id=job_id, exception=error, **kwargs)
    
    def log_compression_metrics(self, job_id: str, metrics: Dict[str, Any], **kwargs):
        """Log compression metrics"""
        self.info(LogComponent.COMPRESSION, "Compression metrics recorded", 
                 job_id=job_id, extra_data=metrics, **kwargs)
    
    def log_motion_analysis_results(self, job_id: str, results: Dict[str, Any], **kwargs):
        """Log motion analysis results"""
        self.info(LogComponent.MOTION_DETECTION, "Motion analysis completed", 
                 job_id=job_id, extra_data=results, **kwargs)
    
    # Query methods
    def get_logs(self, component: Optional[LogComponent] = None,
                level: Optional[LogLevel] = None,
                job_id: Optional[str] = None,
                start_time: Optional[datetime] = None,
                end_time: Optional[datetime] = None,
                limit: int = 100) -> List[Dict[str, Any]]:
        """Query logs based on filters"""
        # This is a simplified implementation
        # In a real system, you might use a proper log management solution
        
        log_file = self.log_dir / f"{self.app_name}.log"
        
        if not log_file.exists():
            return []
        
        logs = []
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        if self.json_logging:
                            log_data = json.loads(line.strip())
                        else:
                            # Parse standard log format (simplified)
                            continue
                        
                        # Apply filters
                        if component and log_data.get('component') != component.value:
                            continue
                        
                        if level and log_data.get('level') != level.value:
                            continue
                        
                        if job_id and log_data.get('job_id') != job_id:
                            continue
                        
                        if start_time:
                            log_time = datetime.fromisoformat(log_data.get('timestamp', ''))
                            if log_time < start_time:
                                continue
                        
                        if end_time:
                            log_time = datetime.fromisoformat(log_data.get('timestamp', ''))
                            if log_time > end_time:
                                continue
                        
                        logs.append(log_data)
                        
                        if len(logs) >= limit:
                            break
                    
                    except (json.JSONDecodeError, ValueError):
                        continue
        
        except Exception as e:
            self.error(LogComponent.SYSTEM, f"Error reading logs: {e}")
        
        return logs[::-1]  # Return most recent first
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors in the last N hours"""
        end_time = datetime.now()
        start_time = end_time - datetime.timedelta(hours=hours)
        
        error_logs = self.get_logs(
            level=LogLevel.ERROR,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        
        # Group errors by component and message
        error_summary = {}
        for log in error_logs:
            component = log.get('component', 'unknown')
            message = log.get('message', 'unknown')
            
            key = f"{component}:{message}"
            if key not in error_summary:
                error_summary[key] = {
                    'count': 0,
                    'component': component,
                    'message': message,
                    'first_occurrence': log.get('timestamp'),
                    'last_occurrence': log.get('timestamp')
                }
            
            error_summary[key]['count'] += 1
            error_summary[key]['last_occurrence'] = log.get('timestamp')
        
        return {
            'period_hours': hours,
            'total_errors': len(error_logs),
            'unique_errors': len(error_summary),
            'error_details': list(error_summary.values())
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics"""
        with self._stats_lock:
            return self.log_stats.copy()
    
    def export_logs(self, output_file: str, **filters):
        """Export filtered logs to file"""
        logs = self.get_logs(**filters)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            if output_path.suffix.lower() == '.json':
                json.dump(logs, f, indent=2)
            else:
                # Export as text
                for log in logs:
                    timestamp = log.get('timestamp', '')
                    level = log.get('level', '')
                    component = log.get('component', '')
                    message = log.get('message', '')
                    job_id = log.get('job_id', '')
                    
                    line = f"{timestamp} [{level}] {component}"
                    if job_id:
                        line += f" [Job: {job_id}]"
                    line += f": {message}\n"
                    
                    f.write(line)


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields
        if hasattr(record, 'job_id') and record.job_id:
            log_data['job_id'] = record.job_id
        
        if hasattr(record, 'user_id') and record.user_id:
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'request_id') and record.request_id:
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'component') and record.component:
            log_data['component'] = record.component
        
        # Add exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET
        
        # Format: [TIMESTAMP] [LEVEL] component: message
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        component = getattr(record, 'component', record.module)
        job_id = getattr(record, 'job_id', '')
        
        formatted = f"[{timestamp}] {color}[{record.levelname}]{reset} {component}"
        
        if job_id:
            formatted += f" [Job: {job_id}]"
        
        formatted += f": {record.getMessage()}"
        
        return formatted


# Global logger instance
logger = CompressorLogger()


# Convenience functions for easier importing
def get_logger() -> CompressorLogger:
    """Get the global logger instance"""
    return logger


def setup_logging(log_dir: str = "./logs", **kwargs):
    """Setup logging with custom configuration"""
    global logger
    logger = CompressorLogger(log_dir=log_dir, **kwargs)
    return logger