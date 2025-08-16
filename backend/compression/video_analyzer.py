import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

from compression.motion_detector import MotionDetector, MotionAnalysisResult, ActivitySegment


@dataclass
class VideoAnalysisReport:
    """Comprehensive video analysis report"""
    file_path: str
    file_size_mb: float
    duration_seconds: float
    resolution: Tuple[int, int]
    fps: float
    codec: str
    motion_analysis: MotionAnalysisResult
    behavioral_insights: Dict[str, Any]
    recommendations: Dict[str, Any]
    analysis_timestamp: str


class VideoAnalyzer:
    """
    Advanced video analyzer for mouse behavior research
    """
    
    def __init__(self, motion_detector: Optional[MotionDetector] = None):
        self.motion_detector = motion_detector or MotionDetector()
        
    def analyze_video_comprehensive(self, video_path: str, 
                                  output_dir: Optional[str] = None,
                                  generate_visualizations: bool = True,
                                  progress_callback: Optional[callable] = None) -> VideoAnalysisReport:
        """
        Perform comprehensive video analysis including motion, behavior patterns, and recommendations
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Get basic video properties
        video_info = self._get_video_properties(video_path)
        
        # Perform motion analysis
        if progress_callback:
            progress_callback(0, "Starting motion analysis...")
        
        motion_analysis = self.motion_detector.analyze_video(
            video_path, 
            progress_callback=lambda p, stage: progress_callback(p * 0.7, f"Motion analysis: {stage}") if progress_callback else None
        )
        
        # Analyze behavioral patterns
        if progress_callback:
            progress_callback(70, "Analyzing behavioral patterns...")
        
        behavioral_insights = self._analyze_behavioral_patterns(motion_analysis, video_info)
        
        # Generate recommendations
        if progress_callback:
            progress_callback(85, "Generating recommendations...")
        
        recommendations = self._generate_compression_recommendations(
            video_info, motion_analysis, behavioral_insights
        )
        
        # Create comprehensive report
        report = VideoAnalysisReport(
            file_path=video_path,
            file_size_mb=video_info['size_mb'],
            duration_seconds=video_info['duration'],
            resolution=(video_info['width'], video_info['height']),
            fps=video_info['fps'],
            codec=video_info['codec'],
            motion_analysis=motion_analysis,
            behavioral_insights=behavioral_insights,
            recommendations=recommendations,
            analysis_timestamp=datetime.now().isoformat()
        )
        
        # Generate visualizations and save report
        if output_dir and generate_visualizations:
            if progress_callback:
                progress_callback(90, "Generating visualizations...")
            
            self._generate_analysis_visualizations(report, output_dir)
            self._save_analysis_report(report, output_dir)
        
        if progress_callback:
            progress_callback(100, "Analysis completed")
        
        return report
    
    def _get_video_properties(self, video_path: str) -> Dict[str, Any]:
        """Extract basic video properties"""
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        props = {
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'codec': self._get_codec_name(cap),
            'size_mb': os.path.getsize(video_path) / (1024 * 1024)
        }
        
        props['duration'] = props['frame_count'] / props['fps'] if props['fps'] > 0 else 0
        
        cap.release()
        return props
    
    def _get_codec_name(self, cap: cv2.VideoCapture) -> str:
        """Get codec name from video capture"""
        fourcc = cap.get(cv2.CAP_PROP_FOURCC)
        codec = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)])
        return codec.strip()
    
    def _analyze_behavioral_patterns(self, motion_analysis: MotionAnalysisResult, 
                                   video_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze behavioral patterns from motion data
        """
        segments = motion_analysis.activity_segments
        timeline = motion_analysis.motion_timeline
        
        # Activity distribution
        activity_distribution = self._calculate_activity_distribution(segments)
        
        # Circadian patterns (if video is long enough)
        circadian_analysis = self._analyze_circadian_patterns(segments, motion_analysis.total_duration)
        
        # Bout analysis (periods of continuous activity/inactivity)
        bout_analysis = self._analyze_activity_bouts(segments)
        
        # Movement intensity patterns
        intensity_analysis = self._analyze_movement_intensity(timeline, motion_analysis.fps)
        
        # Sleep-wake cycle analysis
        sleep_wake_analysis = self._analyze_sleep_wake_cycles(
            motion_analysis.sleep_periods, 
            motion_analysis.active_periods,
            motion_analysis.total_duration
        )
        
        return {
            'activity_distribution': activity_distribution,
            'circadian_patterns': circadian_analysis,
            'bout_analysis': bout_analysis,
            'intensity_analysis': intensity_analysis,
            'sleep_wake_analysis': sleep_wake_analysis,
            'overall_metrics': {
                'total_active_time_minutes': sum([end - start for start, end in motion_analysis.active_periods]) / 60,
                'total_sleep_time_minutes': sum([end - start for start, end in motion_analysis.sleep_periods]) / 60,
                'activity_ratio': motion_analysis.overall_activity_ratio,
                'average_motion_intensity': np.mean(timeline),
                'peak_motion_intensity': np.max(timeline),
                'motion_variability': np.std(timeline)
            }
        }
    
    def _calculate_activity_distribution(self, segments: List[ActivitySegment]) -> Dict[str, float]:
        """Calculate time distribution across activity levels"""
        distribution = {'high': 0, 'medium': 0, 'low': 0, 'inactive': 0}
        total_time = 0
        
        for segment in segments:
            duration = segment.end_time - segment.start_time
            distribution[segment.activity_level] += duration
            total_time += duration
        
        # Convert to percentages
        if total_time > 0:
            for level in distribution:
                distribution[level] = (distribution[level] / total_time) * 100
        
        return distribution
    
    def _analyze_circadian_patterns(self, segments: List[ActivitySegment], 
                                  total_duration: float) -> Dict[str, Any]:
        """
        Analyze circadian patterns if video is long enough (>12 hours)
        """
        if total_duration < 12 * 3600:  # Less than 12 hours
            return {
                'available': False,
                'reason': 'Video too short for circadian analysis (minimum 12 hours)',
                'duration_hours': total_duration / 3600
            }
        
        # Divide into hourly bins
        num_hours = int(total_duration / 3600)
        hourly_activity = np.zeros(num_hours)
        
        for segment in segments:
            start_hour = int(segment.start_time / 3600)
            end_hour = int(segment.end_time / 3600)
            
            activity_score = {'high': 3, 'medium': 2, 'low': 1, 'inactive': 0}[segment.activity_level]
            
            for hour in range(start_hour, min(end_hour + 1, num_hours)):
                hourly_activity[hour] += activity_score
        
        # Find peak activity periods
        peak_hours = np.argsort(hourly_activity)[-3:]  # Top 3 hours
        low_hours = np.argsort(hourly_activity)[:3]    # Bottom 3 hours
        
        return {
            'available': True,
            'duration_hours': num_hours,
            'hourly_activity_scores': hourly_activity.tolist(),
            'peak_activity_hours': peak_hours.tolist(),
            'low_activity_hours': low_hours.tolist(),
            'activity_rhythm_strength': np.std(hourly_activity),
            'peak_activity_time': f"{peak_hours[0]:02d}:00-{peak_hours[0]+1:02d}:00"
        }
    
    def _analyze_activity_bouts(self, segments: List[ActivitySegment]) -> Dict[str, Any]:
        """
        Analyze bouts of continuous activity or inactivity
        """
        active_bouts = []
        inactive_bouts = []
        
        current_bout_start = None
        current_bout_type = None
        
        for segment in segments:
            is_active = segment.activity_level in ['high', 'medium', 'low']
            
            if current_bout_type is None:
                current_bout_start = segment.start_time
                current_bout_type = 'active' if is_active else 'inactive'
            elif (is_active and current_bout_type == 'inactive') or (not is_active and current_bout_type == 'active'):
                # Bout type changed
                bout_duration = segment.start_time - current_bout_start
                
                if current_bout_type == 'active':
                    active_bouts.append(bout_duration)
                else:
                    inactive_bouts.append(bout_duration)
                
                current_bout_start = segment.start_time
                current_bout_type = 'active' if is_active else 'inactive'
        
        # Handle final bout
        if segments and current_bout_start is not None:
            final_duration = segments[-1].end_time - current_bout_start
            if current_bout_type == 'active':
                active_bouts.append(final_duration)
            else:
                inactive_bouts.append(final_duration)
        
        def analyze_bout_list(bouts):
            if not bouts:
                return {'count': 0, 'mean_duration': 0, 'max_duration': 0, 'min_duration': 0}
            return {
                'count': len(bouts),
                'mean_duration_minutes': np.mean(bouts) / 60,
                'max_duration_minutes': np.max(bouts) / 60,
                'min_duration_minutes': np.min(bouts) / 60,
                'std_duration_minutes': np.std(bouts) / 60
            }
        
        return {
            'active_bouts': analyze_bout_list(active_bouts),
            'inactive_bouts': analyze_bout_list(inactive_bouts),
            'total_bouts': len(active_bouts) + len(inactive_bouts)
        }
    
    def _analyze_movement_intensity(self, timeline: List[float], fps: float) -> Dict[str, Any]:
        """
        Analyze movement intensity patterns over time
        """
        timeline_array = np.array(timeline)
        
        # Calculate moving averages
        window_size_minutes = 5
        window_frames = int(window_size_minutes * 60 * fps)
        
        if len(timeline) > window_frames:
            moving_avg = np.convolve(timeline_array, 
                                   np.ones(window_frames)/window_frames, 
                                   mode='valid')
        else:
            moving_avg = timeline_array
        
        # Find peaks and valleys
        from scipy.signal import find_peaks
        
        peaks, _ = find_peaks(moving_avg, height=np.mean(moving_avg) + np.std(moving_avg))
        valleys, _ = find_peaks(-moving_avg, height=-(np.mean(moving_avg) - np.std(moving_avg)))
        
        # Intensity distribution
        intensity_bins = np.histogram(timeline_array, bins=10, range=(0, 1))
        
        return {
            'mean_intensity': float(np.mean(timeline_array)),
            'median_intensity': float(np.median(timeline_array)),
            'std_intensity': float(np.std(timeline_array)),
            'peak_intensity': float(np.max(timeline_array)),
            'intensity_peaks': {
                'count': len(peaks),
                'average_interval_minutes': len(timeline) / len(peaks) / fps / 60 if len(peaks) > 0 else 0
            },
            'intensity_distribution': {
                'bins': intensity_bins[1].tolist(),
                'counts': intensity_bins[0].tolist()
            }
        }
    
    def _analyze_sleep_wake_cycles(self, sleep_periods: List[Tuple[float, float]], 
                                 active_periods: List[Tuple[float, float]],
                                 total_duration: float) -> Dict[str, Any]:
        """
        Analyze sleep-wake cycle patterns
        """
        if not sleep_periods and not active_periods:
            return {'available': False, 'reason': 'No distinct sleep-wake cycles detected'}
        
        sleep_durations = [(end - start) / 60 for start, end in sleep_periods]  # Convert to minutes
        wake_durations = [(end - start) / 60 for start, end in active_periods]
        
        total_sleep_time = sum(sleep_durations)
        total_wake_time = sum(wake_durations)
        
        return {
            'available': True,
            'sleep_periods': {
                'count': len(sleep_periods),
                'total_minutes': total_sleep_time,
                'average_duration_minutes': np.mean(sleep_durations) if sleep_durations else 0,
                'longest_sleep_minutes': max(sleep_durations) if sleep_durations else 0,
                'shortest_sleep_minutes': min(sleep_durations) if sleep_durations else 0
            },
            'wake_periods': {
                'count': len(active_periods),
                'total_minutes': total_wake_time,
                'average_duration_minutes': np.mean(wake_durations) if wake_durations else 0,
                'longest_wake_minutes': max(wake_durations) if wake_durations else 0,
                'shortest_wake_minutes': min(wake_durations) if wake_durations else 0
            },
            'sleep_efficiency': total_sleep_time / (total_duration / 60) * 100,  # Percentage of time sleeping
            'fragmentation_index': len(sleep_periods) + len(active_periods)  # Higher = more fragmented
        }
    
    def _generate_compression_recommendations(self, video_info: Dict[str, Any],
                                            motion_analysis: MotionAnalysisResult,
                                            behavioral_insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate intelligent compression recommendations based on analysis
        """
        recommendations = {}
        
        # Analyze compression suitability
        activity_ratio = motion_analysis.overall_activity_ratio
        file_size_mb = video_info['size_mb']
        duration_hours = video_info['duration'] / 3600
        
        # Profile recommendations based on content
        if activity_ratio > 0.7:
            recommended_profile = "conservative"
            reason = "High activity content requires quality preservation"
        elif activity_ratio < 0.3:
            recommended_profile = "aggressive"
            reason = "Low activity content allows for aggressive compression"
        else:
            recommended_profile = "balanced"
            reason = "Moderate activity levels suit balanced compression"
        
        # Adjust based on file size
        if file_size_mb > 1000:
            if recommended_profile == "conservative":
                recommended_profile = "balanced"
                reason += "; large file size benefits from more compression"
        elif file_size_mb < 100:
            if recommended_profile == "aggressive":
                recommended_profile = "balanced"
                reason += "; small file size allows for less aggressive compression"
        
        recommendations['profile'] = {
            'recommended': recommended_profile,
            'reason': reason,
            'confidence': self._calculate_recommendation_confidence(
                activity_ratio, file_size_mb, duration_hours
            )
        }
        
        # ROI recommendations
        avg_motion = np.mean(motion_analysis.motion_timeline)
        recommendations['roi_compression'] = {
            'recommended': avg_motion > 0.02,
            'reason': f"Average motion intensity ({avg_motion:.3f}) {'supports' if avg_motion > 0.02 else 'does not support'} ROI-based compression",
            'expected_benefit': "10-15% additional space savings" if avg_motion > 0.02 else "Limited benefit expected"
        }
        
        # Segment-based recommendations
        num_segments = len(motion_analysis.activity_segments)
        segment_variability = np.std([s.motion_intensity for s in motion_analysis.activity_segments])
        
        recommendations['adaptive_compression'] = {
            'segments_detected': num_segments,
            'variability_score': float(segment_variability),
            'expected_benefit': self._estimate_adaptive_benefit(activity_ratio, segment_variability),
            'recommended': segment_variability > 0.02
        }
        
        # Quality preservation recommendations
        important_periods = []
        for period_start, period_end in motion_analysis.active_periods:
            if period_end - period_start > 300:  # Periods longer than 5 minutes
                important_periods.append((period_start, period_end))
        
        recommendations['quality_preservation'] = {
            'critical_periods_detected': len(important_periods),
            'critical_periods': important_periods,
            'recommendation': "Use conservative settings during detected active periods" if important_periods else "Standard compression suitable"
        }
        
        return recommendations
    
    def _calculate_recommendation_confidence(self, activity_ratio: float, 
                                          file_size_mb: float, 
                                          duration_hours: float) -> float:
        """Calculate confidence score for recommendations (0-1)"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for clear activity patterns
        if activity_ratio > 0.8 or activity_ratio < 0.2:
            confidence += 0.3
        elif activity_ratio > 0.6 or activity_ratio < 0.4:
            confidence += 0.1
        
        # Higher confidence for longer videos (more data)
        if duration_hours > 12:
            confidence += 0.2
        elif duration_hours > 6:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _estimate_adaptive_benefit(self, activity_ratio: float, 
                                 segment_variability: float) -> str:
        """Estimate benefit of adaptive compression"""
        if segment_variability > 0.05:
            return "High benefit - significant activity variation detected"
        elif segment_variability > 0.02:
            return "Moderate benefit - some activity variation detected"
        else:
            return "Limited benefit - uniform activity patterns"
    
    def _generate_analysis_visualizations(self, report: VideoAnalysisReport, output_dir: str):
        """Generate visualization plots for the analysis"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Motion timeline plot
        self._plot_motion_timeline(report.motion_analysis, 
                                 os.path.join(output_dir, "motion_timeline.png"))
        
        # Activity distribution pie chart
        self._plot_activity_distribution(report.behavioral_insights['activity_distribution'],
                                       os.path.join(output_dir, "activity_distribution.png"))
        
        # Sleep-wake cycles
        if report.behavioral_insights['sleep_wake_analysis']['available']:
            self._plot_sleep_wake_cycles(report.motion_analysis,
                                       os.path.join(output_dir, "sleep_wake_cycles.png"))
        
        # Circadian patterns (if available)
        if report.behavioral_insights['circadian_patterns']['available']:
            self._plot_circadian_patterns(report.behavioral_insights['circadian_patterns'],
                                        os.path.join(output_dir, "circadian_patterns.png"))
    
    def _plot_motion_timeline(self, motion_analysis: MotionAnalysisResult, output_path: str):
        """Plot motion intensity timeline"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Motion intensity over time
        time_axis = np.arange(len(motion_analysis.motion_timeline)) / motion_analysis.fps / 60  # minutes
        ax1.plot(time_axis, motion_analysis.motion_timeline, linewidth=0.5, alpha=0.7)
        ax1.set_xlabel('Time (minutes)')
        ax1.set_ylabel('Motion Intensity')
        ax1.set_title('Motion Intensity Timeline')
        ax1.grid(True, alpha=0.3)
        
        # Activity segments
        colors = {'high': 'red', 'medium': 'orange', 'low': 'yellow', 'inactive': 'blue'}
        for segment in motion_analysis.activity_segments:
            start_min = segment.start_time / 60
            end_min = segment.end_time / 60
            ax2.barh(0, end_min - start_min, left=start_min, 
                    color=colors[segment.activity_level], alpha=0.7, height=0.5)
        
        ax2.set_xlabel('Time (minutes)')
        ax2.set_ylabel('Activity Level')
        ax2.set_title('Activity Segments')
        ax2.set_ylim(-0.5, 0.5)
        ax2.set_yticks([])
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=colors[level], label=level.title()) 
                          for level in colors.keys()]
        ax2.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_activity_distribution(self, distribution: Dict[str, float], output_path: str):
        """Plot activity level distribution"""
        fig, ax = plt.subplots(figsize=(10, 8))
        
        levels = list(distribution.keys())
        percentages = list(distribution.values())
        colors = ['red', 'orange', 'yellow', 'blue']
        
        wedges, texts, autotexts = ax.pie(percentages, labels=levels, colors=colors, 
                                         autopct='%1.1f%%', startangle=90)
        
        ax.set_title('Activity Level Distribution', fontsize=16)
        
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_sleep_wake_cycles(self, motion_analysis: MotionAnalysisResult, output_path: str):
        """Plot sleep-wake cycles"""
        fig, ax = plt.subplots(figsize=(15, 6))
        
        # Plot sleep periods in blue
        for start, end in motion_analysis.sleep_periods:
            ax.barh(0, (end - start)/60, left=start/60, color='blue', alpha=0.7, height=0.4)
        
        # Plot wake periods in red
        for start, end in motion_analysis.active_periods:
            ax.barh(0, (end - start)/60, left=start/60, color='red', alpha=0.7, height=0.4)
        
        ax.set_xlabel('Time (minutes)')
        ax.set_ylabel('Sleep/Wake State')
        ax.set_title('Sleep-Wake Cycles')
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.grid(True, alpha=0.3)
        
        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='blue', label='Sleep'),
            Patch(facecolor='red', label='Wake')
        ]
        ax.legend(handles=legend_elements)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_circadian_patterns(self, circadian_data: Dict[str, Any], output_path: str):
        """Plot circadian activity patterns"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        hours = range(len(circadian_data['hourly_activity_scores']))
        scores = circadian_data['hourly_activity_scores']
        
        ax.bar(hours, scores, alpha=0.7, color='green')
        ax.set_xlabel('Hour of Day')
        ax.set_ylabel('Activity Score')
        ax.set_title('Circadian Activity Pattern')
        ax.set_xticks(range(0, 24, 2))
        ax.grid(True, alpha=0.3)
        
        # Highlight peak hours
        for hour in circadian_data['peak_activity_hours']:
            if hour < len(scores):
                ax.bar(hour, scores[hour], color='red', alpha=0.8)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
    
    def _save_analysis_report(self, report: VideoAnalysisReport, output_dir: str):
        """Save comprehensive analysis report as JSON"""
        report_path = os.path.join(output_dir, "analysis_report.json")
        
        # Convert to serializable format
        report_dict = {
            'file_path': report.file_path,
            'file_size_mb': report.file_size_mb,
            'duration_seconds': report.duration_seconds,
            'resolution': report.resolution,
            'fps': report.fps,
            'codec': report.codec,
            'motion_analysis': {
                'total_duration': report.motion_analysis.total_duration,
                'total_frames': report.motion_analysis.total_frames,
                'fps': report.motion_analysis.fps,
                'activity_segments': [asdict(seg) for seg in report.motion_analysis.activity_segments],
                'motion_timeline': report.motion_analysis.motion_timeline,
                'sleep_periods': report.motion_analysis.sleep_periods,
                'active_periods': report.motion_analysis.active_periods,
                'overall_activity_ratio': report.motion_analysis.overall_activity_ratio
            },
            'behavioral_insights': report.behavioral_insights,
            'recommendations': report.recommendations,
            'analysis_timestamp': report.analysis_timestamp
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
    
    def compare_videos(self, video_paths: List[str], output_dir: str) -> Dict[str, Any]:
        """
        Compare multiple videos for behavioral analysis
        """
        reports = []
        
        for video_path in video_paths:
            try:
                report = self.analyze_video_comprehensive(video_path, generate_visualizations=False)
                reports.append(report)
            except Exception as e:
                print(f"Failed to analyze {video_path}: {e}")
                continue
        
        if not reports:
            raise ValueError("No videos were successfully analyzed")
        
        # Generate comparison metrics
        comparison = {
            'videos_analyzed': len(reports),
            'activity_ratios': [r.motion_analysis.overall_activity_ratio for r in reports],
            'file_sizes_mb': [r.file_size_mb for r in reports],
            'durations_hours': [r.duration_seconds / 3600 for r in reports],
            'compression_recommendations': {}
        }
        
        # Statistical comparison
        activity_ratios = comparison['activity_ratios']
        comparison['statistics'] = {
            'mean_activity_ratio': np.mean(activity_ratios),
            'std_activity_ratio': np.std(activity_ratios),
            'most_active_video': video_paths[np.argmax(activity_ratios)],
            'least_active_video': video_paths[np.argmin(activity_ratios)]
        }
        
        # Compression recommendations for batch processing
        avg_activity = np.mean(activity_ratios)
        total_size = sum(comparison['file_sizes_mb'])
        
        if avg_activity > 0.6:
            batch_profile = "conservative"
        elif avg_activity < 0.4:
            batch_profile = "aggressive"
        else:
            batch_profile = "balanced"
        
        comparison['compression_recommendations'] = {
            'batch_profile': batch_profile,
            'estimated_total_savings_mb': total_size * (1 - 0.4),  # Rough estimate
            'processing_time_estimate_hours': len(reports) * 2  # Rough estimate
        }
        
        # Save comparison report
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "video_comparison.json"), 'w') as f:
            json.dump(comparison, f, indent=2)
        
        return comparison