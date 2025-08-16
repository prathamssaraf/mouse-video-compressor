import ffmpeg
import subprocess
import os
import json
import tempfile
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass
import shutil
from pathlib import Path
import time
import threading
import queue

from compression.motion_detector import MotionDetector, MotionAnalysisResult, ActivitySegment
from compression.compression_profiles import (
    CompressionProfileManager, CompressionProfile, ActivityCompressionProfile,
    CompressionSettings, ROICompressionSettings, CompressionValidator
)


@dataclass
class CompressionJob:
    job_id: str
    input_path: str
    output_path: str
    profile: ActivityCompressionProfile
    motion_analysis: MotionAnalysisResult
    status: str = "pending"  # pending, running, completed, failed, cancelled
    progress: float = 0.0
    current_segment: int = 0
    total_segments: int = 0
    error_message: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    original_size_mb: float = 0.0
    compressed_size_mb: float = 0.0


class AdaptiveCompressor:
    """
    Adaptive video compressor that adjusts compression based on motion analysis
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.profile_manager = CompressionProfileManager()
        self.roi_settings = ROICompressionSettings()
        self.motion_detector = MotionDetector()
        
        # Job management
        self.active_jobs: Dict[str, CompressionJob] = {}
        self.job_threads: Dict[str, threading.Thread] = {}
        self.progress_callbacks: Dict[str, Callable] = {}
        
        # Verify FFmpeg installation
        self._verify_ffmpeg()
    
    def _verify_ffmpeg(self):
        """Verify FFmpeg is installed and accessible"""
        try:
            result = subprocess.run([self.ffmpeg_path, '-version'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("FFmpeg not found or not working")
        except FileNotFoundError:
            raise RuntimeError(f"FFmpeg not found at {self.ffmpeg_path}")
    
    def start_compression_job(self, job_id: str, input_path: str, output_path: str,
                            profile_type: CompressionProfile,
                            custom_profile_name: Optional[str] = None,
                            progress_callback: Optional[Callable] = None,
                            roi_enabled: bool = True) -> CompressionJob:
        """
        Start a new compression job
        """
        # Get compression profile
        profile = self.profile_manager.get_profile(profile_type, custom_profile_name)
        
        # Validate input file
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Get original file size
        original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
        
        # Create job with placeholder motion analysis
        job = CompressionJob(
            job_id=job_id,
            input_path=input_path,
            output_path=output_path,
            profile=profile,
            motion_analysis=None,  # Will be populated during processing
            original_size_mb=original_size
        )
        
        self.active_jobs[job_id] = job
        
        if progress_callback:
            self.progress_callbacks[job_id] = progress_callback
        
        # Start compression in separate thread
        thread = threading.Thread(
            target=self._compress_video_worker,
            args=(job_id, roi_enabled),
            daemon=True
        )
        self.job_threads[job_id] = thread
        thread.start()
        
        return job
    
    def _compress_video_worker(self, job_id: str, roi_enabled: bool):
        """
        Worker function for video compression
        """
        job = self.active_jobs[job_id]
        
        try:
            job.status = "running"
            job.start_time = time.time()
            
            # Step 1: Analyze motion (20% of progress)
            self._update_progress(job_id, 0.0, "Analyzing motion patterns...")
            
            def motion_progress_callback(progress, stage):
                self._update_progress(job_id, progress * 0.2 / 100, f"Motion analysis: {stage}")
            
            motion_analysis = self.motion_detector.analyze_video(
                job.input_path, 
                progress_callback=motion_progress_callback
            )
            job.motion_analysis = motion_analysis
            job.total_segments = len(motion_analysis.activity_segments)
            
            # Step 2: Compress video segments (80% of progress)
            self._update_progress(job_id, 20.0, "Starting adaptive compression...")
            
            if len(motion_analysis.activity_segments) == 0:
                # Fallback: compress entire video with balanced settings
                self._compress_single_segment(job_id, roi_enabled)
            else:
                # Adaptive compression based on segments
                self._compress_adaptive_segments(job_id, roi_enabled)
            
            # Finalize job
            job.status = "completed"
            job.end_time = time.time()
            job.compressed_size_mb = os.path.getsize(job.output_path) / (1024 * 1024)
            
            self._update_progress(job_id, 100.0, "Compression completed successfully")
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.end_time = time.time()
            self._update_progress(job_id, job.progress, f"Error: {str(e)}")
            
            # Clean up partial output
            if os.path.exists(job.output_path):
                try:
                    os.remove(job.output_path)
                except:
                    pass
    
    def _compress_adaptive_segments(self, job_id: str, roi_enabled: bool):
        """
        Compress video using adaptive settings for each segment
        """
        job = self.active_jobs[job_id]
        segments = job.motion_analysis.activity_segments
        
        # Create temporary directory for segment files
        with tempfile.TemporaryDirectory() as temp_dir:
            segment_files = []
            
            # Process each segment
            for i, segment in enumerate(segments):
                job.current_segment = i + 1
                
                segment_progress_start = 20 + (i / len(segments)) * 70
                segment_progress_end = 20 + ((i + 1) / len(segments)) * 70
                
                self._update_progress(
                    job_id, 
                    segment_progress_start,
                    f"Compressing segment {i+1}/{len(segments)} ({segment.activity_level})"
                )
                
                # Get compression settings for this segment's activity level
                settings = self.profile_manager.get_settings_for_activity(
                    job.profile, segment.activity_level
                )
                
                # Apply ROI adjustments if enabled
                if roi_enabled:
                    # Check if this segment has significant motion for ROI
                    has_roi = segment.motion_intensity > 0.02
                    settings = self.roi_settings.adjust_settings_for_roi(settings, has_roi)
                
                # Create segment file
                segment_file = os.path.join(temp_dir, f"segment_{i:04d}.mp4")
                
                self._compress_video_segment(
                    job.input_path,
                    segment_file,
                    settings,
                    segment.start_time,
                    segment.end_time - segment.start_time,
                    lambda p: self._update_progress(
                        job_id,
                        segment_progress_start + (p * (segment_progress_end - segment_progress_start) / 100),
                        f"Compressing segment {i+1}/{len(segments)} ({segment.activity_level}): {p:.1f}%"
                    )
                )
                
                segment_files.append(segment_file)
            
            # Concatenate all segments
            self._update_progress(job_id, 90.0, "Combining compressed segments...")
            self._concatenate_segments(segment_files, job.output_path)
    
    def _compress_single_segment(self, job_id: str, roi_enabled: bool):
        """
        Compress entire video as single segment (fallback method)
        """
        job = self.active_jobs[job_id]
        
        # Use balanced settings as fallback
        settings = self.profile_manager.get_settings_for_activity(
            job.profile, "medium"
        )
        
        def progress_callback(progress):
            actual_progress = 20 + (progress * 70 / 100)
            self._update_progress(job_id, actual_progress, f"Compressing video: {progress:.1f}%")
        
        self._compress_video_segment(
            job.input_path,
            job.output_path,
            settings,
            0,
            None,  # Full duration
            progress_callback
        )
    
    def _compress_video_segment(self, input_path: str, output_path: str,
                              settings: CompressionSettings,
                              start_time: float, duration: Optional[float],
                              progress_callback: Optional[Callable] = None):
        """
        Compress a specific segment of video with given settings
        """
        # Build FFmpeg command
        input_stream = ffmpeg.input(input_path, ss=start_time)
        
        if duration is not None:
            input_stream = ffmpeg.input(input_path, ss=start_time, t=duration)
        
        # Get FFmpeg arguments from settings
        ffmpeg_args = settings.to_ffmpeg_args()
        
        # Build output stream
        output_stream = ffmpeg.output(input_stream, output_path, **ffmpeg_args)
        
        # Run compression with progress tracking
        cmd = ffmpeg.compile(output_stream, overwrite_output=True)
        
        if progress_callback:
            self._run_ffmpeg_with_progress(cmd, progress_callback, duration)
        else:
            subprocess.run(cmd, check=True, capture_output=True)
    
    def _run_ffmpeg_with_progress(self, cmd: List[str], 
                                progress_callback: Callable,
                                duration: Optional[float]):
        """
        Run FFmpeg command with progress tracking
        """
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        while True:
            output = process.stderr.readline()
            if output == '' and process.poll() is not None:
                break
            
            if output and progress_callback and duration:
                # Parse FFmpeg progress output
                if "time=" in output:
                    try:
                        time_str = output.split("time=")[1].split()[0]
                        current_time = self._parse_time_string(time_str)
                        if current_time and duration > 0:
                            progress = min(100.0, (current_time / duration) * 100)
                            progress_callback(progress)
                    except:
                        pass
        
        # Wait for completion and check return code
        return_code = process.poll()
        if return_code != 0:
            stderr = process.stderr.read()
            raise RuntimeError(f"FFmpeg failed: {stderr}")
    
    def _parse_time_string(self, time_str: str) -> Optional[float]:
        """
        Parse FFmpeg time string (HH:MM:SS.mmm) to seconds
        """
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except:
            pass
        return None
    
    def _concatenate_segments(self, segment_files: List[str], output_path: str):
        """
        Concatenate video segments using FFmpeg
        """
        # Create temporary file list for FFmpeg concat
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            list_file = f.name
            for segment_file in segment_files:
                f.write(f"file '{segment_file}'\n")
        
        try:
            # Run FFmpeg concat
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Concatenation failed: {result.stderr}")
                
        finally:
            # Clean up temp file
            try:
                os.unlink(list_file)
            except:
                pass
    
    def _update_progress(self, job_id: str, progress: float, message: str):
        """
        Update job progress and notify callback
        """
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.progress = progress
            
            if job_id in self.progress_callbacks:
                self.progress_callbacks[job_id](job_id, progress, message)
    
    def get_job_status(self, job_id: str) -> Optional[CompressionJob]:
        """
        Get current status of compression job
        """
        return self.active_jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running compression job
        """
        if job_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[job_id]
        
        if job.status == "running":
            job.status = "cancelled"
            
            # The thread will check this status and exit
            if job_id in self.job_threads:
                # Note: We can't forcibly kill the thread, but FFmpeg processes
                # will eventually finish and the thread will check the status
                pass
            
            # Clean up partial output
            if os.path.exists(job.output_path):
                try:
                    os.remove(job.output_path)
                except:
                    pass
            
            return True
        
        return False
    
    def cleanup_job(self, job_id: str):
        """
        Clean up completed job resources
        """
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
        
        if job_id in self.job_threads:
            del self.job_threads[job_id]
        
        if job_id in self.progress_callbacks:
            del self.progress_callbacks[job_id]
    
    def get_video_info(self, video_path: str) -> Dict:
        """
        Get video information using ffprobe
        """
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                raise ValueError("No video stream found")
            
            info = {
                'duration': float(probe['format']['duration']),
                'size_bytes': int(probe['format']['size']),
                'size_mb': int(probe['format']['size']) / (1024 * 1024),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),
                'codec': video_stream['codec_name'],
                'bitrate': int(probe['format'].get('bit_rate', 0))
            }
            
            return info
            
        except Exception as e:
            raise RuntimeError(f"Failed to get video info: {str(e)}")
    
    def estimate_output_size(self, video_info: Dict, 
                           profile: ActivityCompressionProfile,
                           motion_analysis: Optional[MotionAnalysisResult] = None) -> Dict:
        """
        Estimate output file size based on profile and motion analysis
        """
        base_compression_ratio = profile.expected_compression_ratio
        
        # Adjust based on actual activity if motion analysis available
        if motion_analysis:
            activity_ratio = motion_analysis.overall_activity_ratio
            
            # More active content compresses less efficiently
            activity_adjustment = 1.0 + (activity_ratio * 0.3)
            adjusted_ratio = base_compression_ratio * activity_adjustment
        else:
            adjusted_ratio = base_compression_ratio
        
        estimated_size_mb = video_info['size_mb'] * adjusted_ratio
        estimated_size_bytes = estimated_size_mb * 1024 * 1024
        
        return {
            'estimated_size_mb': round(estimated_size_mb, 1),
            'estimated_size_bytes': int(estimated_size_bytes),
            'compression_ratio': adjusted_ratio,
            'space_saved_mb': round(video_info['size_mb'] - estimated_size_mb, 1),
            'space_saved_percent': round((1 - adjusted_ratio) * 100, 1)
        }


class CompressionBenchmark:
    """
    Benchmark compression performance and quality
    """
    
    def __init__(self, compressor: AdaptiveCompressor):
        self.compressor = compressor
    
    def run_quality_benchmark(self, input_path: str, output_dir: str) -> Dict:
        """
        Run compression with different profiles and measure quality/size
        """
        results = {}
        
        for profile_type in CompressionProfile:
            if profile_type == CompressionProfile.CUSTOM:
                continue
            
            output_path = os.path.join(
                output_dir, 
                f"benchmark_{profile_type.value}.mp4"
            )
            
            job_id = f"benchmark_{profile_type.value}"
            
            start_time = time.time()
            job = self.compressor.start_compression_job(
                job_id, input_path, output_path, profile_type
            )
            
            # Wait for completion
            while job.status in ["pending", "running"]:
                time.sleep(1)
                job = self.compressor.get_job_status(job_id)
            
            end_time = time.time()
            
            if job.status == "completed":
                results[profile_type.value] = {
                    'profile': profile_type.value,
                    'original_size_mb': job.original_size_mb,
                    'compressed_size_mb': job.compressed_size_mb,
                    'compression_ratio': job.compressed_size_mb / job.original_size_mb,
                    'space_saved_percent': (1 - job.compressed_size_mb / job.original_size_mb) * 100,
                    'processing_time_seconds': end_time - start_time,
                    'output_path': output_path
                }
            else:
                results[profile_type.value] = {
                    'profile': profile_type.value,
                    'error': job.error_message,
                    'status': job.status
                }
            
            # Cleanup
            self.compressor.cleanup_job(job_id)
        
        return results