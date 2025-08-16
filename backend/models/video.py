from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum
import os


class VideoFormat(str, Enum):
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    WMV = "wmv"
    MKV = "mkv"


class VideoStatus(str, Enum):
    AVAILABLE = "available"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    DELETED = "deleted"


class VideoMetadata(BaseModel):
    """Video file metadata"""
    duration: float = Field(..., description="Duration in seconds")
    fps: float = Field(..., description="Frames per second")
    width: int = Field(..., description="Video width in pixels")
    height: int = Field(..., description="Video height in pixels")
    codec: str = Field(..., description="Video codec")
    bitrate: Optional[int] = Field(None, description="Bitrate in bits/second")
    frame_count: int = Field(..., description="Total number of frames")
    
    @validator('duration', 'fps')
    def validate_positive_numbers(cls, v):
        if v <= 0:
            raise ValueError('Duration and FPS must be positive')
        return v
    
    @validator('width', 'height', 'frame_count')
    def validate_positive_integers(cls, v):
        if v <= 0:
            raise ValueError('Width, height, and frame count must be positive')
        return v


class VideoThumbnail(BaseModel):
    """Video thumbnail information"""
    timestamp: float = Field(..., description="Timestamp in seconds where thumbnail was captured")
    file_path: str = Field(..., description="Path to thumbnail image file")
    width: int = Field(..., description="Thumbnail width")
    height: int = Field(..., description="Thumbnail height")


class MotionAnalysisSummary(BaseModel):
    """Summary of motion analysis results"""
    overall_activity_ratio: float = Field(..., description="Overall activity ratio (0-1)")
    peak_activity_time: Optional[str] = Field(None, description="Time of peak activity")
    total_active_periods: int = Field(..., description="Number of active periods")
    total_sleep_periods: int = Field(..., description="Number of sleep periods")
    average_motion_intensity: float = Field(..., description="Average motion intensity")
    has_circadian_pattern: bool = Field(..., description="Whether circadian patterns were detected")
    analysis_completed_at: datetime = Field(..., description="When analysis was completed")


class Video(BaseModel):
    """Video model representing a video file in the system"""
    id: str = Field(..., description="Unique video identifier")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Absolute path to video file")
    file_size_bytes: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in megabytes")
    format: VideoFormat = Field(..., description="Video format/extension")
    status: VideoStatus = Field(default=VideoStatus.AVAILABLE, description="Current video status")
    
    # Timestamps
    uploaded_at: datetime = Field(default_factory=datetime.now, description="Upload timestamp")
    last_accessed_at: Optional[datetime] = Field(None, description="Last access timestamp")
    
    # Video properties
    metadata: Optional[VideoMetadata] = Field(None, description="Video metadata")
    thumbnails: List[VideoThumbnail] = Field(default_factory=list, description="Video thumbnails")
    
    # Analysis results
    motion_analysis: Optional[MotionAnalysisSummary] = Field(None, description="Motion analysis summary")
    analysis_file_path: Optional[str] = Field(None, description="Path to detailed analysis file")
    
    # Processing history
    compression_jobs: List[str] = Field(default_factory=list, description="List of compression job IDs")
    
    # User metadata
    tags: List[str] = Field(default_factory=list, description="User-defined tags")
    description: Optional[str] = Field(None, description="User description")
    experiment_id: Optional[str] = Field(None, description="Associated experiment identifier")
    subject_id: Optional[str] = Field(None, description="Subject/mouse identifier")
    
    @validator('file_path')
    def validate_file_exists(cls, v):
        if not os.path.exists(v):
            raise ValueError(f'Video file does not exist: {v}')
        return v
    
    @validator('file_size_bytes')
    def validate_file_size(cls, v):
        if v <= 0:
            raise ValueError('File size must be positive')
        return v
    
    @validator('format')
    def validate_format_matches_extension(cls, v, values):
        if 'filename' in values:
            filename = values['filename']
            extension = filename.split('.')[-1].lower()
            if extension != v.value:
                raise ValueError(f'Format {v} does not match file extension {extension}')
        return v
    
    @property
    def file_size_mb_rounded(self) -> float:
        """File size in MB rounded to 2 decimal places"""
        return round(self.file_size_mb, 2)
    
    @property
    def duration_formatted(self) -> str:
        """Duration formatted as HH:MM:SS"""
        if not self.metadata:
            return "Unknown"
        
        total_seconds = int(self.metadata.duration)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def resolution_string(self) -> str:
        """Resolution as string (e.g., "1920x1080")"""
        if not self.metadata:
            return "Unknown"
        return f"{self.metadata.width}x{self.metadata.height}"
    
    @property
    def has_motion_analysis(self) -> bool:
        """Whether video has completed motion analysis"""
        return self.motion_analysis is not None
    
    @property
    def activity_level_description(self) -> str:
        """Human-readable activity level description"""
        if not self.motion_analysis:
            return "Not analyzed"
        
        ratio = self.motion_analysis.overall_activity_ratio
        if ratio > 0.7:
            return "Very Active"
        elif ratio > 0.5:
            return "Active"
        elif ratio > 0.3:
            return "Moderate"
        elif ratio > 0.1:
            return "Low Activity"
        else:
            return "Minimal Activity"


class VideoListResponse(BaseModel):
    """Response model for video list endpoints"""
    videos: List[Video]
    total_count: int
    page: int
    page_size: int
    total_pages: int


class VideoSearchQuery(BaseModel):
    """Query parameters for video search"""
    query: Optional[str] = Field(None, description="Search query")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    experiment_id: Optional[str] = Field(None, description="Filter by experiment ID")
    subject_id: Optional[str] = Field(None, description="Filter by subject ID")
    min_duration: Optional[float] = Field(None, description="Minimum duration in seconds")
    max_duration: Optional[float] = Field(None, description="Maximum duration in seconds")
    min_file_size_mb: Optional[float] = Field(None, description="Minimum file size in MB")
    max_file_size_mb: Optional[float] = Field(None, description="Maximum file size in MB")
    activity_level: Optional[str] = Field(None, description="Activity level filter")
    has_analysis: Optional[bool] = Field(None, description="Filter by analysis completion")
    format: Optional[VideoFormat] = Field(None, description="Filter by video format")
    uploaded_after: Optional[datetime] = Field(None, description="Uploaded after date")
    uploaded_before: Optional[datetime] = Field(None, description="Uploaded before date")
    sort_by: str = Field(default="uploaded_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")
    page: int = Field(default=1, description="Page number")
    page_size: int = Field(default=20, description="Page size")
    
    @validator('page', 'page_size')
    def validate_pagination(cls, v):
        if v <= 0:
            raise ValueError('Page and page_size must be positive')
        return v
    
    @validator('page_size')
    def validate_page_size_limit(cls, v):
        if v > 100:
            raise ValueError('Page size cannot exceed 100')
        return v
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('Sort order must be "asc" or "desc"')
        return v


class VideoUploadRequest(BaseModel):
    """Request model for video upload"""
    filename: str = Field(..., description="Original filename")
    experiment_id: Optional[str] = Field(None, description="Experiment identifier")
    subject_id: Optional[str] = Field(None, description="Subject identifier")
    description: Optional[str] = Field(None, description="Video description")
    tags: List[str] = Field(default_factory=list, description="Tags")
    auto_analyze: bool = Field(default=True, description="Automatically start motion analysis")


class VideoUpdateRequest(BaseModel):
    """Request model for video updates"""
    description: Optional[str] = Field(None, description="Updated description")
    tags: Optional[List[str]] = Field(None, description="Updated tags")
    experiment_id: Optional[str] = Field(None, description="Updated experiment ID")
    subject_id: Optional[str] = Field(None, description="Updated subject ID")


class VideoAnalysisRequest(BaseModel):
    """Request model for video analysis"""
    video_id: str = Field(..., description="Video ID to analyze")
    force_reanalysis: bool = Field(default=False, description="Force re-analysis if already done")
    generate_visualizations: bool = Field(default=True, description="Generate visualization plots")
    save_detailed_results: bool = Field(default=True, description="Save detailed analysis results")


class VideoPreviewRequest(BaseModel):
    """Request model for video preview generation"""
    video_id: str = Field(..., description="Video ID")
    timestamps: List[float] = Field(..., description="Timestamps for preview frames (seconds)")
    width: Optional[int] = Field(None, description="Preview width (maintains aspect ratio if not specified)")
    height: Optional[int] = Field(None, description="Preview height (maintains aspect ratio if not specified)")
    include_motion_overlay: bool = Field(default=False, description="Include motion detection overlay")


class VideoStatsResponse(BaseModel):
    """Response model for video statistics"""
    total_videos: int
    total_size_gb: float
    total_duration_hours: float
    analyzed_videos: int
    average_activity_ratio: float
    format_distribution: Dict[str, int]
    activity_distribution: Dict[str, int]
    recent_uploads: int  # Last 7 days
    
    
class VideoBatchOperation(BaseModel):
    """Request model for batch operations on videos"""
    video_ids: List[str] = Field(..., description="List of video IDs")
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    
    @validator('operation')
    def validate_operation(cls, v):
        valid_operations = [
            'analyze', 'compress', 'delete', 'tag', 'export_analysis'
        ]
        if v not in valid_operations:
            raise ValueError(f'Invalid operation. Must be one of: {valid_operations}')
        return v
    
    @validator('video_ids')
    def validate_video_ids(cls, v):
        if not v:
            raise ValueError('At least one video ID must be provided')
        if len(v) > 50:
            raise ValueError('Cannot process more than 50 videos in a single batch')
        return v