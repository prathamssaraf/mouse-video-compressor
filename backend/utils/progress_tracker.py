import asyncio
import json
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
from collections import defaultdict, deque


class ProgressEventType(str, Enum):
    STARTED = "started"
    PROGRESS = "progress"
    STAGE_CHANGED = "stage_changed"
    ERROR = "error"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ProgressEvent:
    job_id: str
    event_type: ProgressEventType
    timestamp: datetime
    percentage: float
    stage: str
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class ProgressSnapshot:
    """Snapshot of progress at a specific time"""
    percentage: float
    stage: str
    message: str
    timestamp: datetime
    estimated_completion: Optional[datetime] = None
    processing_speed: Optional[float] = None  # e.g., frames per second
    data: Optional[Dict[str, Any]] = None


class ProgressHistory:
    """Maintains progress history for a job"""
    
    def __init__(self, max_snapshots: int = 100):
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.events: deque = deque(maxlen=max_snapshots)
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def add_snapshot(self, snapshot: ProgressSnapshot):
        if not self.start_time:
            self.start_time = snapshot.timestamp
        self.snapshots.append(snapshot)
    
    def add_event(self, event: ProgressEvent):
        self.events.append(event)
        if event.event_type in [ProgressEventType.COMPLETED, ProgressEventType.CANCELLED, ProgressEventType.ERROR]:
            self.end_time = event.timestamp
    
    def get_duration(self) -> Optional[timedelta]:
        if self.start_time:
            end = self.end_time or datetime.now()
            return end - self.start_time
        return None
    
    def get_average_speed(self) -> Optional[float]:
        """Calculate average progress speed (percentage per second)"""
        if len(self.snapshots) < 2:
            return None
        
        first = self.snapshots[0]
        last = self.snapshots[-1]
        
        time_diff = (last.timestamp - first.timestamp).total_seconds()
        progress_diff = last.percentage - first.percentage
        
        if time_diff > 0:
            return progress_diff / time_diff
        return None
    
    def estimate_completion(self, current_percentage: float) -> Optional[datetime]:
        """Estimate completion time based on historical progress"""
        speed = self.get_average_speed()
        if speed and speed > 0 and current_percentage < 100:
            remaining_percentage = 100 - current_percentage
            estimated_seconds = remaining_percentage / speed
            return datetime.now() + timedelta(seconds=estimated_seconds)
        return None


class ProgressTracker:
    """
    Centralized progress tracking system for video compression jobs
    """
    
    def __init__(self):
        self.job_progress: Dict[str, ProgressHistory] = {}
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.global_subscribers: List[Callable] = []
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        
        # Threading support
        self._lock = threading.RLock()
        self._event_queue = queue.Queue()
        self._worker_thread = None
        self._running = False
        
        # Performance tracking
        self.performance_stats = {
            'total_jobs_tracked': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0,
            'average_completion_time': 0.0
        }
    
    def start_tracking(self):
        """Start the background worker thread"""
        with self._lock:
            if not self._running:
                self._running = True
                self._worker_thread = threading.Thread(target=self._event_worker, daemon=True)
                self._worker_thread.start()
    
    def stop_tracking(self):
        """Stop the background worker thread"""
        with self._lock:
            self._running = False
            if self._worker_thread:
                self._worker_thread.join(timeout=5.0)
    
    def _event_worker(self):
        """Background worker to process events"""
        while self._running:
            try:
                event = self._event_queue.get(timeout=1.0)
                self._process_event(event)
                self._event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing progress event: {e}")
    
    def _process_event(self, event: ProgressEvent):
        """Process a progress event"""
        with self._lock:
            # Update history
            if event.job_id not in self.job_progress:
                self.job_progress[event.job_id] = ProgressHistory()
            
            history = self.job_progress[event.job_id]
            history.add_event(event)
            
            # Create snapshot if it's a progress event
            if event.event_type == ProgressEventType.PROGRESS:
                snapshot = ProgressSnapshot(
                    percentage=event.percentage,
                    stage=event.stage,
                    message=event.message,
                    timestamp=event.timestamp,
                    estimated_completion=history.estimate_completion(event.percentage),
                    data=event.data
                )
                history.add_snapshot(snapshot)
            
            # Update active jobs
            if event.event_type == ProgressEventType.STARTED:
                self.active_jobs[event.job_id] = {
                    'start_time': event.timestamp,
                    'current_stage': event.stage,
                    'current_percentage': event.percentage
                }
            elif event.event_type in [ProgressEventType.COMPLETED, ProgressEventType.CANCELLED, ProgressEventType.ERROR]:
                if event.job_id in self.active_jobs:
                    del self.active_jobs[event.job_id]
                
                # Update performance stats
                if event.event_type == ProgressEventType.COMPLETED:
                    self.performance_stats['completed_jobs'] += 1
                elif event.event_type == ProgressEventType.ERROR:
                    self.performance_stats['failed_jobs'] += 1
                elif event.event_type == ProgressEventType.CANCELLED:
                    self.performance_stats['cancelled_jobs'] += 1
            
            # Notify subscribers
            self._notify_subscribers(event)
    
    def register_job(self, job_id: str, initial_stage: str = "initializing") -> bool:
        """Register a new job for tracking"""
        event = ProgressEvent(
            job_id=job_id,
            event_type=ProgressEventType.STARTED,
            timestamp=datetime.now(),
            percentage=0.0,
            stage=initial_stage,
            message="Job started"
        )
        
        self._event_queue.put(event)
        self.performance_stats['total_jobs_tracked'] += 1
        return True
    
    def update_progress(self, job_id: str, percentage: float, 
                       stage: Optional[str] = None,
                       message: Optional[str] = None,
                       data: Optional[Dict[str, Any]] = None):
        """Update progress for a job"""
        with self._lock:
            current_info = self.active_jobs.get(job_id, {})
            
            event = ProgressEvent(
                job_id=job_id,
                event_type=ProgressEventType.PROGRESS,
                timestamp=datetime.now(),
                percentage=max(0, min(100, percentage)),
                stage=stage or current_info.get('current_stage', 'unknown'),
                message=message or f"Progress: {percentage:.1f}%",
                data=data
            )
            
            self._event_queue.put(event)
            
            # Update active job info
            if job_id in self.active_jobs:
                self.active_jobs[job_id].update({
                    'current_percentage': event.percentage,
                    'current_stage': event.stage,
                    'last_update': event.timestamp
                })
    
    def change_stage(self, job_id: str, new_stage: str, message: Optional[str] = None):
        """Change the current stage of a job"""
        event = ProgressEvent(
            job_id=job_id,
            event_type=ProgressEventType.STAGE_CHANGED,
            timestamp=datetime.now(),
            percentage=self.get_current_percentage(job_id),
            stage=new_stage,
            message=message or f"Stage changed to: {new_stage}"
        )
        
        self._event_queue.put(event)
    
    def complete_job(self, job_id: str, message: str = "Job completed successfully"):
        """Mark a job as completed"""
        event = ProgressEvent(
            job_id=job_id,
            event_type=ProgressEventType.COMPLETED,
            timestamp=datetime.now(),
            percentage=100.0,
            stage="completed",
            message=message
        )
        
        self._event_queue.put(event)
    
    def fail_job(self, job_id: str, error_message: str, 
                error_data: Optional[Dict[str, Any]] = None):
        """Mark a job as failed"""
        event = ProgressEvent(
            job_id=job_id,
            event_type=ProgressEventType.ERROR,
            timestamp=datetime.now(),
            percentage=self.get_current_percentage(job_id),
            stage="error",
            message=error_message,
            data=error_data
        )
        
        self._event_queue.put(event)
    
    def cancel_job(self, job_id: str, message: str = "Job cancelled"):
        """Mark a job as cancelled"""
        event = ProgressEvent(
            job_id=job_id,
            event_type=ProgressEventType.CANCELLED,
            timestamp=datetime.now(),
            percentage=self.get_current_percentage(job_id),
            stage="cancelled",
            message=message
        )
        
        self._event_queue.put(event)
    
    def get_current_percentage(self, job_id: str) -> float:
        """Get current progress percentage for a job"""
        with self._lock:
            if job_id in self.active_jobs:
                return self.active_jobs[job_id].get('current_percentage', 0.0)
            
            if job_id in self.job_progress and self.job_progress[job_id].snapshots:
                return self.job_progress[job_id].snapshots[-1].percentage
            
            return 0.0
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status for a job"""
        with self._lock:
            if job_id not in self.job_progress:
                return None
            
            history = self.job_progress[job_id]
            
            # Get latest snapshot
            latest_snapshot = history.snapshots[-1] if history.snapshots else None
            latest_event = history.events[-1] if history.events else None
            
            # Determine current status
            is_active = job_id in self.active_jobs
            
            status = {
                'job_id': job_id,
                'is_active': is_active,
                'current_percentage': latest_snapshot.percentage if latest_snapshot else 0.0,
                'current_stage': latest_snapshot.stage if latest_snapshot else 'unknown',
                'current_message': latest_snapshot.message if latest_snapshot else '',
                'start_time': history.start_time,
                'end_time': history.end_time,
                'duration': history.get_duration(),
                'estimated_completion': latest_snapshot.estimated_completion if latest_snapshot else None,
                'average_speed': history.get_average_speed(),
                'last_event_type': latest_event.event_type if latest_event else None,
                'last_update': latest_snapshot.timestamp if latest_snapshot else None
            }
            
            return status
    
    def get_active_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all active jobs"""
        with self._lock:
            active_statuses = {}
            for job_id in self.active_jobs:
                status = self.get_job_status(job_id)
                if status:
                    active_statuses[job_id] = status
            return active_statuses
    
    def get_job_history(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get complete history for a job"""
        with self._lock:
            if job_id not in self.job_progress:
                return None
            
            history = self.job_progress[job_id]
            
            return {
                'job_id': job_id,
                'snapshots': [asdict(snapshot) for snapshot in history.snapshots],
                'events': [asdict(event) for event in history.events],
                'start_time': history.start_time,
                'end_time': history.end_time,
                'duration': history.get_duration(),
                'average_speed': history.get_average_speed()
            }
    
    def subscribe_to_job(self, job_id: str, callback: Callable[[ProgressEvent], None]):
        """Subscribe to progress updates for a specific job"""
        with self._lock:
            self.subscribers[job_id].append(callback)
    
    def subscribe_to_all(self, callback: Callable[[ProgressEvent], None]):
        """Subscribe to all progress updates"""
        with self._lock:
            self.global_subscribers.append(callback)
    
    def unsubscribe_from_job(self, job_id: str, callback: Callable[[ProgressEvent], None]):
        """Unsubscribe from job-specific updates"""
        with self._lock:
            if job_id in self.subscribers and callback in self.subscribers[job_id]:
                self.subscribers[job_id].remove(callback)
    
    def unsubscribe_from_all(self, callback: Callable[[ProgressEvent], None]):
        """Unsubscribe from global updates"""
        with self._lock:
            if callback in self.global_subscribers:
                self.global_subscribers.remove(callback)
    
    def _notify_subscribers(self, event: ProgressEvent):
        """Notify relevant subscribers about an event"""
        # Notify job-specific subscribers
        for callback in self.subscribers.get(event.job_id, []):
            try:
                callback(event)
            except Exception as e:
                print(f"Error in progress callback: {e}")
        
        # Notify global subscribers
        for callback in self.global_subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in global progress callback: {e}")
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up progress data for old jobs"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._lock:
            jobs_to_remove = []
            
            for job_id, history in self.job_progress.items():
                if (history.end_time and history.end_time < cutoff_time and 
                    job_id not in self.active_jobs):
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.job_progress[job_id]
                if job_id in self.subscribers:
                    del self.subscribers[job_id]
    
    def export_progress_data(self, job_id: str, format: str = "json") -> Optional[str]:
        """Export progress data for a job"""
        history_data = self.get_job_history(job_id)
        
        if not history_data:
            return None
        
        if format.lower() == "json":
            # Convert datetime objects to ISO strings for JSON serialization
            def convert_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, timedelta):
                    return obj.total_seconds()
                return obj
            
            # Deep convert datetime objects
            def convert_nested(data):
                if isinstance(data, dict):
                    return {k: convert_nested(v) for k, v in data.items()}
                elif isinstance(data, list):
                    return [convert_nested(item) for item in data]
                else:
                    return convert_datetime(data)
            
            converted_data = convert_nested(history_data)
            return json.dumps(converted_data, indent=2)
        
        return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics"""
        with self._lock:
            total_duration = 0
            completed_count = 0
            
            for history in self.job_progress.values():
                if history.end_time and history.start_time:
                    duration = history.get_duration()
                    if duration:
                        total_duration += duration.total_seconds()
                        completed_count += 1
            
            stats = self.performance_stats.copy()
            
            if completed_count > 0:
                stats['average_completion_time'] = total_duration / completed_count
            
            stats.update({
                'active_jobs_count': len(self.active_jobs),
                'total_jobs_in_history': len(self.job_progress),
                'success_rate': (stats['completed_jobs'] / max(1, stats['total_jobs_tracked'])) * 100
            })
            
            return stats


class ProgressReporter:
    """
    Helper class for easier progress reporting within job functions
    """
    
    def __init__(self, tracker: ProgressTracker, job_id: str):
        self.tracker = tracker
        self.job_id = job_id
        self.current_stage = "initializing"
        self.stage_weights = {}  # stage_name -> weight (percentage of total)
        self.stage_progress = {}  # stage_name -> current progress within stage
        
    def set_stage_weights(self, weights: Dict[str, float]):
        """Set relative weights for different stages"""
        total_weight = sum(weights.values())
        self.stage_weights = {stage: (weight / total_weight) * 100 
                            for stage, weight in weights.items()}
    
    def start_stage(self, stage_name: str, message: Optional[str] = None):
        """Start a new processing stage"""
        self.current_stage = stage_name
        self.stage_progress[stage_name] = 0.0
        
        self.tracker.change_stage(
            self.job_id, 
            stage_name, 
            message or f"Starting {stage_name}"
        )
    
    def update_stage_progress(self, stage_progress: float, message: Optional[str] = None):
        """Update progress within the current stage"""
        self.stage_progress[self.current_stage] = max(0, min(100, stage_progress))
        
        # Calculate overall progress
        overall_progress = self._calculate_overall_progress()
        
        self.tracker.update_progress(
            self.job_id,
            overall_progress,
            self.current_stage,
            message
        )
    
    def _calculate_overall_progress(self) -> float:
        """Calculate overall progress based on stage weights"""
        if not self.stage_weights:
            return self.stage_progress.get(self.current_stage, 0.0)
        
        total_progress = 0.0
        
        for stage, weight in self.stage_weights.items():
            if stage in self.stage_progress:
                stage_contribution = (self.stage_progress[stage] / 100) * weight
                total_progress += stage_contribution
        
        return total_progress
    
    def complete(self, message: str = "Processing completed successfully"):
        """Mark the job as completed"""
        self.tracker.complete_job(self.job_id, message)
    
    def fail(self, error_message: str, error_data: Optional[Dict[str, Any]] = None):
        """Mark the job as failed"""
        self.tracker.fail_job(self.job_id, error_message, error_data)
    
    def cancel(self, message: str = "Processing cancelled"):
        """Mark the job as cancelled"""
        self.tracker.cancel_job(self.job_id, message)