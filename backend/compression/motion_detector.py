import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta


@dataclass
class ActivitySegment:
    start_time: float
    end_time: float
    activity_level: str  # 'high', 'medium', 'low', 'inactive'
    motion_intensity: float
    frame_start: int
    frame_end: int


@dataclass
class MotionAnalysisResult:
    total_duration: float
    total_frames: int
    fps: float
    activity_segments: List[ActivitySegment]
    motion_timeline: List[float]
    sleep_periods: List[Tuple[float, float]]
    active_periods: List[Tuple[float, float]]
    overall_activity_ratio: float


class MotionDetector:
    def __init__(self, 
                 motion_threshold: float = 0.02,
                 background_learning_rate: float = 0.001,
                 min_inactive_duration: int = 30,
                 gaussian_blur_kernel: int = 21,
                 morphology_kernel_size: int = 5):
        
        self.motion_threshold = motion_threshold
        self.background_learning_rate = background_learning_rate
        self.min_inactive_duration = min_inactive_duration
        self.gaussian_blur_kernel = gaussian_blur_kernel
        self.morphology_kernel_size = morphology_kernel_size
        
        # Initialize background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True,
            varThreshold=16,
            history=500
        )
        
        # Morphological operations kernel
        self.kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, 
            (self.morphology_kernel_size, self.morphology_kernel_size)
        )
        
        # Activity classification thresholds
        self.activity_thresholds = {
            'high': 0.08,
            'medium': 0.04,
            'low': 0.01,
            'inactive': 0.0
        }

    def analyze_video(self, video_path: str, 
                     progress_callback: Optional[callable] = None) -> MotionAnalysisResult:
        """
        Analyze video for motion patterns and activity detection
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps
        
        motion_timeline = []
        frame_count = 0
        prev_gray = None
        
        # Initialize optical flow parameters
        lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        # Feature detection parameters
        feature_params = dict(
            maxCorners=100,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate motion intensity for current frame
            motion_intensity = self._calculate_motion_intensity(
                frame, prev_gray, lk_params, feature_params
            )
            motion_timeline.append(motion_intensity)
            
            # Update previous frame
            prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            frame_count += 1
            
            # Progress callback
            if progress_callback and frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100
                progress_callback(progress, "motion_analysis")
        
        cap.release()
        
        # Generate activity segments
        activity_segments = self._generate_activity_segments(
            motion_timeline, fps
        )
        
        # Identify sleep and active periods
        sleep_periods, active_periods = self._identify_sleep_wake_cycles(
            activity_segments
        )
        
        # Calculate overall activity ratio
        total_active_time = sum([end - start for start, end in active_periods])
        activity_ratio = total_active_time / duration if duration > 0 else 0
        
        return MotionAnalysisResult(
            total_duration=duration,
            total_frames=total_frames,
            fps=fps,
            activity_segments=activity_segments,
            motion_timeline=motion_timeline,
            sleep_periods=sleep_periods,
            active_periods=active_periods,
            overall_activity_ratio=activity_ratio
        )

    def _calculate_motion_intensity(self, frame: np.ndarray, 
                                  prev_gray: Optional[np.ndarray],
                                  lk_params: dict,
                                  feature_params: dict) -> float:
        """
        Calculate motion intensity using multiple methods
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Background subtraction
        fg_mask = self.bg_subtractor.apply(frame, learningRate=self.background_learning_rate)
        
        # Clean up the mask
        fg_mask = cv2.GaussianBlur(fg_mask, (self.gaussian_blur_kernel, self.gaussian_blur_kernel), 0)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel)
        
        # Calculate motion area ratio
        motion_area = cv2.countNonZero(fg_mask)
        total_area = frame.shape[0] * frame.shape[1]
        bg_motion_ratio = motion_area / total_area
        
        # Method 2: Optical flow (if previous frame exists)
        optical_flow_intensity = 0.0
        if prev_gray is not None:
            # Detect features to track
            corners = cv2.goodFeaturesToTrack(prev_gray, mask=None, **feature_params)
            
            if corners is not None and len(corners) > 0:
                # Calculate optical flow
                new_corners, status, error = cv2.calcOpticalFlowPyrLK(
                    prev_gray, gray, corners, None, **lk_params
                )
                
                # Calculate motion vectors
                if new_corners is not None:
                    good_new = new_corners[status == 1]
                    good_old = corners[status == 1]
                    
                    if len(good_new) > 0:
                        motion_vectors = good_new - good_old
                        motion_magnitudes = np.sqrt(
                            motion_vectors[:, 0]**2 + motion_vectors[:, 1]**2
                        )
                        optical_flow_intensity = np.mean(motion_magnitudes) / 100.0  # Normalize
        
        # Method 3: Frame differencing
        frame_diff_intensity = 0.0
        if prev_gray is not None:
            diff = cv2.absdiff(prev_gray, gray)
            diff_blur = cv2.GaussianBlur(diff, (self.gaussian_blur_kernel, self.gaussian_blur_kernel), 0)
            _, thresh = cv2.threshold(diff_blur, 20, 255, cv2.THRESH_BINARY)
            frame_diff_intensity = cv2.countNonZero(thresh) / total_area
        
        # Combine motion detection methods
        combined_intensity = (
            bg_motion_ratio * 0.5 + 
            optical_flow_intensity * 0.3 + 
            frame_diff_intensity * 0.2
        )
        
        return min(combined_intensity, 1.0)  # Cap at 1.0

    def _generate_activity_segments(self, motion_timeline: List[float], 
                                  fps: float) -> List[ActivitySegment]:
        """
        Generate activity segments based on motion timeline
        """
        segments = []
        current_segment_start = 0
        current_activity_level = self._classify_activity(motion_timeline[0])
        segment_motion_values = [motion_timeline[0]]
        
        for i, motion_value in enumerate(motion_timeline[1:], 1):
            activity_level = self._classify_activity(motion_value)
            
            # Check if activity level changed or we've reached a natural break
            if (activity_level != current_activity_level or 
                i - current_segment_start >= fps * 10):  # Max 10 second segments
                
                # Create segment for previous period
                segment = ActivitySegment(
                    start_time=current_segment_start / fps,
                    end_time=i / fps,
                    activity_level=current_activity_level,
                    motion_intensity=np.mean(segment_motion_values),
                    frame_start=current_segment_start,
                    frame_end=i
                )
                segments.append(segment)
                
                # Start new segment
                current_segment_start = i
                current_activity_level = activity_level
                segment_motion_values = [motion_value]
            else:
                segment_motion_values.append(motion_value)
        
        # Add final segment
        if current_segment_start < len(motion_timeline):
            segment = ActivitySegment(
                start_time=current_segment_start / fps,
                end_time=len(motion_timeline) / fps,
                activity_level=current_activity_level,
                motion_intensity=np.mean(segment_motion_values),
                frame_start=current_segment_start,
                frame_end=len(motion_timeline)
            )
            segments.append(segment)
        
        return segments

    def _classify_activity(self, motion_intensity: float) -> str:
        """
        Classify motion intensity into activity levels
        """
        if motion_intensity >= self.activity_thresholds['high']:
            return 'high'
        elif motion_intensity >= self.activity_thresholds['medium']:
            return 'medium'
        elif motion_intensity >= self.activity_thresholds['low']:
            return 'low'
        else:
            return 'inactive'

    def _identify_sleep_wake_cycles(self, segments: List[ActivitySegment]) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """
        Identify sleep and wake periods based on activity segments
        """
        sleep_periods = []
        active_periods = []
        
        current_inactive_start = None
        current_active_start = None
        
        for segment in segments:
            if segment.activity_level == 'inactive':
                if current_active_start is not None:
                    # End active period
                    active_periods.append((current_active_start, segment.start_time))
                    current_active_start = None
                
                if current_inactive_start is None:
                    current_inactive_start = segment.start_time
            else:
                if current_inactive_start is not None:
                    # Check if inactive period is long enough to be considered sleep
                    inactive_duration = segment.start_time - current_inactive_start
                    if inactive_duration >= self.min_inactive_duration:
                        sleep_periods.append((current_inactive_start, segment.start_time))
                    current_inactive_start = None
                
                if current_active_start is None:
                    current_active_start = segment.start_time
        
        # Handle final periods
        if current_inactive_start is not None:
            final_time = segments[-1].end_time
            if final_time - current_inactive_start >= self.min_inactive_duration:
                sleep_periods.append((current_inactive_start, final_time))
        
        if current_active_start is not None:
            active_periods.append((current_active_start, segments[-1].end_time))
        
        return sleep_periods, active_periods

    def get_roi_around_mouse(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect mouse location and return ROI (Region of Interest)
        Returns (x, y, width, height) or None if no mouse detected
        """
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Clean up the mask
        fg_mask = cv2.GaussianBlur(fg_mask, (self.gaussian_blur_kernel, self.gaussian_blur_kernel), 0)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, self.kernel)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Find largest contour (assumed to be the mouse)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Get bounding rectangle with some padding
        x, y, w, h = cv2.boundingRect(largest_contour)
        padding = 50
        
        # Add padding and ensure within frame bounds
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(frame.shape[1] - x, w + 2 * padding)
        h = min(frame.shape[0] - y, h + 2 * padding)
        
        # Only return ROI if it's reasonably sized (filter out noise)
        if w > 20 and h > 20 and cv2.contourArea(largest_contour) > 100:
            return (x, y, w, h)
        
        return None

    def save_analysis_results(self, results: MotionAnalysisResult, output_path: str):
        """
        Save motion analysis results to JSON file
        """
        # Convert to serializable format
        data = {
            'total_duration': results.total_duration,
            'total_frames': results.total_frames,
            'fps': results.fps,
            'activity_segments': [asdict(segment) for segment in results.activity_segments],
            'motion_timeline': results.motion_timeline,
            'sleep_periods': results.sleep_periods,
            'active_periods': results.active_periods,
            'overall_activity_ratio': results.overall_activity_ratio,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

    def visualize_motion_overlay(self, frame: np.ndarray, motion_intensity: float) -> np.ndarray:
        """
        Create visualization overlay showing motion detection
        """
        overlay = frame.copy()
        
        # Add motion intensity bar
        bar_height = 20
        bar_width = int(frame.shape[1] * 0.3)
        bar_x = frame.shape[1] - bar_width - 20
        bar_y = 20
        
        # Background bar
        cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (0, 0, 0), -1)
        
        # Motion intensity bar
        intensity_width = int(bar_width * motion_intensity)
        color = (0, 255, 0) if motion_intensity < 0.03 else (0, 255, 255) if motion_intensity < 0.08 else (0, 0, 255)
        cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + intensity_width, bar_y + bar_height), color, -1)
        
        # Motion intensity text
        text = f"Motion: {motion_intensity:.3f}"
        cv2.putText(overlay, text, (bar_x, bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Get ROI and draw bounding box
        roi = self.get_roi_around_mouse(frame)
        if roi:
            x, y, w, h = roi
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(overlay, "Mouse ROI", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        
        return overlay