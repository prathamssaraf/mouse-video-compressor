from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class CompressionProfile(Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


@dataclass
class CompressionSettings:
    """Settings for a specific activity level"""
    crf: int  # Constant Rate Factor (lower = higher quality)
    fps: int  # Target frame rate
    preset: str  # FFmpeg preset (ultrafast, fast, medium, slow, veryslow)
    profile: str  # H.264 profile (baseline, main, high)
    bitrate_factor: float  # Multiplier for bitrate calculation
    
    def to_ffmpeg_args(self) -> Dict[str, Any]:
        """Convert to FFmpeg arguments"""
        return {
            'crf': self.crf,
            'r': self.fps,
            'preset': self.preset,
            'profile:v': self.profile,
            'c:v': 'libx264',
            'pix_fmt': 'yuv420p'
        }


@dataclass
class ActivityCompressionProfile:
    """Compression settings for different activity levels"""
    high_activity: CompressionSettings
    medium_activity: CompressionSettings
    low_activity: CompressionSettings
    inactive: CompressionSettings
    name: str
    description: str
    expected_compression_ratio: float


class CompressionProfileManager:
    """Manages compression profiles and settings"""
    
    def __init__(self):
        self.profiles = self._create_default_profiles()
        self.custom_profiles = {}
    
    def _create_default_profiles(self) -> Dict[CompressionProfile, ActivityCompressionProfile]:
        """Create default compression profiles"""
        profiles = {}
        
        # Conservative Profile - Research Priority
        profiles[CompressionProfile.CONSERVATIVE] = ActivityCompressionProfile(
            name="Conservative (Research Priority)",
            description="Prioritizes quality retention, minimal compression during active periods",
            expected_compression_ratio=0.45,
            high_activity=CompressionSettings(
                crf=18,
                fps=30,
                preset="slow",
                profile="high",
                bitrate_factor=1.0
            ),
            medium_activity=CompressionSettings(
                crf=20,
                fps=25,
                preset="slow", 
                profile="high",
                bitrate_factor=0.8
            ),
            low_activity=CompressionSettings(
                crf=23,
                fps=20,
                preset="medium",
                profile="main",
                bitrate_factor=0.6
            ),
            inactive=CompressionSettings(
                crf=25,
                fps=15,
                preset="medium",
                profile="main",
                bitrate_factor=0.4
            )
        )
        
        # Balanced Profile - Default
        profiles[CompressionProfile.BALANCED] = ActivityCompressionProfile(
            name="Balanced (Default)",
            description="Good balance between quality and file size reduction",
            expected_compression_ratio=0.35,
            high_activity=CompressionSettings(
                crf=21,
                fps=25,
                preset="medium",
                profile="high",
                bitrate_factor=0.9
            ),
            medium_activity=CompressionSettings(
                crf=24,
                fps=20,
                preset="medium",
                profile="main",
                bitrate_factor=0.7
            ),
            low_activity=CompressionSettings(
                crf=27,
                fps=15,
                preset="fast",
                profile="main",
                bitrate_factor=0.5
            ),
            inactive=CompressionSettings(
                crf=28,
                fps=10,
                preset="fast",
                profile="baseline",
                bitrate_factor=0.3
            )
        )
        
        # Aggressive Profile - Storage Priority  
        profiles[CompressionProfile.AGGRESSIVE] = ActivityCompressionProfile(
            name="Aggressive (Storage Priority)",
            description="Maximum compression, prioritizes storage savings",
            expected_compression_ratio=0.20,
            high_activity=CompressionSettings(
                crf=23,
                fps=20,
                preset="fast",
                profile="main",
                bitrate_factor=0.8
            ),
            medium_activity=CompressionSettings(
                crf=26,
                fps=15,
                preset="fast",
                profile="main",
                bitrate_factor=0.6
            ),
            low_activity=CompressionSettings(
                crf=30,
                fps=10,
                preset="fast",
                profile="baseline",
                bitrate_factor=0.4
            ),
            inactive=CompressionSettings(
                crf=32,
                fps=5,
                preset="ultrafast",
                profile="baseline",
                bitrate_factor=0.2
            )
        )
        
        return profiles
    
    def get_profile(self, profile_type: CompressionProfile, 
                   custom_name: Optional[str] = None) -> ActivityCompressionProfile:
        """Get a compression profile"""
        if profile_type == CompressionProfile.CUSTOM and custom_name:
            if custom_name in self.custom_profiles:
                return self.custom_profiles[custom_name]
            else:
                raise ValueError(f"Custom profile '{custom_name}' not found")
        
        if profile_type in self.profiles:
            return self.profiles[profile_type]
        else:
            raise ValueError(f"Profile type '{profile_type}' not supported")
    
    def get_settings_for_activity(self, profile: ActivityCompressionProfile, 
                                activity_level: str) -> CompressionSettings:
        """Get compression settings for specific activity level"""
        activity_map = {
            'high': profile.high_activity,
            'medium': profile.medium_activity,
            'low': profile.low_activity,
            'inactive': profile.inactive
        }
        
        if activity_level not in activity_map:
            raise ValueError(f"Unknown activity level: {activity_level}")
        
        return activity_map[activity_level]
    
    def create_custom_profile(self, name: str, profile: ActivityCompressionProfile):
        """Create a custom compression profile"""
        self.custom_profiles[name] = profile
    
    def list_all_profiles(self) -> Dict[str, ActivityCompressionProfile]:
        """List all available profiles"""
        all_profiles = {}
        
        # Add default profiles
        for profile_type, profile in self.profiles.items():
            all_profiles[profile_type.value] = profile
        
        # Add custom profiles
        for name, profile in self.custom_profiles.items():
            all_profiles[f"custom_{name}"] = profile
        
        return all_profiles
    
    def get_profile_recommendations(self, video_duration: float, 
                                  file_size_mb: float,
                                  activity_ratio: float) -> Dict[str, Dict]:
        """Get profile recommendations based on video characteristics"""
        recommendations = {}
        
        for profile_type, profile in self.profiles.items():
            estimated_size = file_size_mb * profile.expected_compression_ratio
            processing_time_estimate = self._estimate_processing_time(
                video_duration, profile_type
            )
            
            recommendations[profile_type.value] = {
                'profile': profile,
                'estimated_output_size_mb': round(estimated_size, 1),
                'estimated_processing_time_minutes': round(processing_time_estimate, 1),
                'compression_ratio': profile.expected_compression_ratio,
                'recommended_for': self._get_recommendation_reason(
                    profile_type, activity_ratio, file_size_mb
                )
            }
        
        return recommendations
    
    def _estimate_processing_time(self, duration: float, 
                                profile_type: CompressionProfile) -> float:
        """Estimate processing time based on profile and duration"""
        # Base processing speed (minutes of video per minute of processing)
        speed_factors = {
            CompressionProfile.CONSERVATIVE: 0.3,  # Slower due to quality settings
            CompressionProfile.BALANCED: 0.5,     # Medium speed
            CompressionProfile.AGGRESSIVE: 0.8    # Faster due to speed presets
        }
        
        factor = speed_factors.get(profile_type, 0.5)
        return (duration / 60) / factor  # Convert to processing minutes
    
    def _get_recommendation_reason(self, profile_type: CompressionProfile,
                                 activity_ratio: float, file_size_mb: float) -> str:
        """Get reason why this profile is recommended"""
        reasons = []
        
        if profile_type == CompressionProfile.CONSERVATIVE:
            if activity_ratio > 0.7:
                reasons.append("High activity content - quality preservation important")
            if file_size_mb < 500:
                reasons.append("Small file size allows for conservative compression")
        
        elif profile_type == CompressionProfile.BALANCED:
            reasons.append("Good general-purpose choice")
            if 0.3 <= activity_ratio <= 0.7:
                reasons.append("Moderate activity levels suit balanced approach")
        
        elif profile_type == CompressionProfile.AGGRESSIVE:
            if activity_ratio < 0.3:
                reasons.append("Low activity content allows aggressive compression")
            if file_size_mb > 1000:
                reasons.append("Large file size benefits from aggressive compression")
        
        return "; ".join(reasons) if reasons else "Standard recommendation"


class ROICompressionSettings:
    """Settings for Region of Interest based compression"""
    
    def __init__(self):
        self.roi_quality_boost = 3  # CRF reduction for ROI area
        self.background_quality_reduction = 5  # CRF increase for background
        self.roi_padding = 50  # Pixels of padding around detected ROI
        self.enable_roi_compression = True
    
    def adjust_settings_for_roi(self, base_settings: CompressionSettings,
                              has_roi: bool) -> CompressionSettings:
        """Adjust compression settings when ROI is detected"""
        if not self.enable_roi_compression or not has_roi:
            return base_settings
        
        # Create adjusted settings for ROI-based compression
        adjusted_settings = CompressionSettings(
            crf=max(0, base_settings.crf - self.roi_quality_boost),
            fps=base_settings.fps,
            preset=base_settings.preset,
            profile=base_settings.profile,
            bitrate_factor=base_settings.bitrate_factor * 1.2  # Slight bitrate increase
        )
        
        return adjusted_settings


class CompressionValidator:
    """Validates compression settings and parameters"""
    
    @staticmethod
    def validate_settings(settings: CompressionSettings) -> bool:
        """Validate compression settings"""
        if not (0 <= settings.crf <= 51):
            raise ValueError(f"CRF must be between 0-51, got {settings.crf}")
        
        if not (1 <= settings.fps <= 60):
            raise ValueError(f"FPS must be between 1-60, got {settings.fps}")
        
        valid_presets = ['ultrafast', 'superfast', 'veryfast', 'faster', 
                        'fast', 'medium', 'slow', 'slower', 'veryslow']
        if settings.preset not in valid_presets:
            raise ValueError(f"Invalid preset: {settings.preset}")
        
        valid_profiles = ['baseline', 'main', 'high']
        if settings.profile not in valid_profiles:
            raise ValueError(f"Invalid profile: {settings.profile}")
        
        return True
    
    @staticmethod
    def validate_profile(profile: ActivityCompressionProfile) -> bool:
        """Validate activity compression profile"""
        CompressionValidator.validate_settings(profile.high_activity)
        CompressionValidator.validate_settings(profile.medium_activity)
        CompressionValidator.validate_settings(profile.low_activity)
        CompressionValidator.validate_settings(profile.inactive)
        
        # Ensure quality progression makes sense
        crfs = [
            profile.high_activity.crf,
            profile.medium_activity.crf,
            profile.low_activity.crf,
            profile.inactive.crf
        ]
        
        if not all(crfs[i] <= crfs[i+1] for i in range(len(crfs)-1)):
            raise ValueError("CRF values should increase with decreasing activity")
        
        return True