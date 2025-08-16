from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class CompressionProfileType(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class ProcessingStage(str, Enum):
    INITIALIZING = "initializing"
    MOTION_ANALYSIS = "motion_analysis"
    SEGMENT_COMPRESSION = "segment_compression"
    CONCATENATION = "concatenation"
    FINALIZING = "finalizing"
    CLEANUP = "cleanup"


class CompressionSettings(BaseModel):
    """Compression settings for a job"""
    profile_type: CompressionProfileType = Field(..., description="Compression profile type")
    custom_profile_name: Optional[str] = Field(None, description="Name of custom profile if using custom")
    output_format: str = Field(default="mp4", description="Output video format")
    roi_compression_enabled: bool = Field(default=True, description="Enable ROI-based compression")
    preserve_metadata: bool = Field(default=True, description="Preserve original video metadata")
    generate_preview: bool = Field(default=True, description="Generate preview with motion overlay")
    
    # Advanced settings
    max_bitrate_mbps: Optional[float] = Field(None, description="Maximum bitrate in Mbps")
    target_file_size_mb: Optional[float] = Field(None, description="Target output file size in MB")
    quality_boost_active_periods: int = Field(default=3, description="CRF reduction for active periods")
    
    @validator('profile_type')
    def validate_custom_profile(cls, v, values):
        if v == CompressionProfileType.CUSTOM and not values.get('custom_profile_name'):
            raise ValueError('Custom profile name is required when using custom profile type')
        return v


class ProgressInfo(BaseModel):
    """Detailed progress information"""
    percentage: float = Field(..., ge=0, le=100, description="Overall progress percentage")
    current_stage: ProcessingStage = Field(..., description="Current processing stage")
    stage_progress: float = Field(..., ge=0, le=100, description="Progress within current stage")
    current_segment: Optional[int] = Field(None, description="Current segment being processed")
    total_segments: Optional[int] = Field(None, description="Total number of segments")
    estimated_time_remaining_seconds: Optional[float] = Field(None, description="Estimated time remaining in seconds")
    processing_speed_fps: Optional[float] = Field(None, description="Current processing speed in FPS")
    message: str = Field(..., description="Current status message")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last progress update")


class CompressionMetrics(BaseModel):
    """Metrics collected during compression"""
    original_size_bytes: int = Field(..., description="Original file size in bytes")
    compressed_size_bytes: Optional[int] = Field(None, description="Compressed file size in bytes")
    compression_ratio: Optional[float] = Field(None, description="Compression ratio (compressed/original)")
    space_saved_bytes: Optional[int] = Field(None, description="Space saved in bytes")
    space_saved_percentage: Optional[float] = Field(None, description="Space saved as percentage")
    
    # Quality metrics
    average_quality_score: Optional[float] = Field(None, description="Average quality score")
    quality_variance: Optional[float] = Field(None, description="Quality variance across segments")
    
    # Performance metrics
    total_processing_time_seconds: Optional[float] = Field(None, description="Total processing time")
    frames_processed: Optional[int] = Field(None, description="Total frames processed")
    average_processing_fps: Optional[float] = Field(None, description="Average processing speed")
    peak_processing_fps: Optional[float] = Field(None, description="Peak processing speed")
    
    # Motion analysis metrics
    motion_analysis_time_seconds: Optional[float] = Field(None, description="Time spent on motion analysis")
    segments_created: Optional[int] = Field(None, description="Number of segments created")
    activity_ratio: Optional[float] = Field(None, description="Overall activity ratio")


class ErrorInfo(BaseModel):
    """Error information for failed jobs"""
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[str] = Field(None, description="Detailed error information")
    failed_stage: Optional[ProcessingStage] = Field(None, description="Stage where failure occurred")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    is_retryable: bool = Field(default=False, description="Whether the error is retryable")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class OutputFile(BaseModel):
    """Information about output files"""
    file_path: str = Field(..., description="Path to output file")
    file_type: str = Field(..., description="Type of output file")
    file_size_bytes: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    checksum: Optional[str] = Field(None, description="File checksum for integrity verification")


class CompressionJob(BaseModel):
    """Main compression job model"""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique job identifier")
    
    # Input/Output
    input_video_id: str = Field(..., description="ID of input video")
    input_file_path: str = Field(..., description="Path to input video file")
    output_file_path: str = Field(..., description="Path to output video file")
    output_directory: str = Field(..., description="Output directory")
    
    # Job configuration
    settings: CompressionSettings = Field(..., description="Compression settings")
    priority: JobPriority = Field(default=JobPriority.NORMAL, description="Job priority")
    
    # Status and progress
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    progress: ProgressInfo = Field(
        default_factory=lambda: ProgressInfo(
            percentage=0.0,
            current_stage=ProcessingStage.INITIALIZING,
            stage_progress=0.0,
            message="Job created"
        ),
        description="Progress information"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now, description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    
    # Results
    metrics: Optional[CompressionMetrics] = Field(None, description="Compression metrics")
    output_files: List[OutputFile] = Field(default_factory=list, description="Generated output files")
    
    # Error handling
    error_info: Optional[ErrorInfo] = Field(None, description="Error information if job failed")
    
    # Metadata
    created_by: Optional[str] = Field(None, description="User who created the job")
    worker_id: Optional[str] = Field(None, description="ID of worker processing the job")
    parent_job_id: Optional[str] = Field(None, description="Parent job ID for batch operations")
    child_job_ids: List[str] = Field(default_factory=list, description="Child job IDs")
    
    # Analysis results
    motion_analysis_file: Optional[str] = Field(None, description="Path to motion analysis results")
    visualization_files: List[str] = Field(default_factory=list, description="Paths to visualization files")
    
    @validator('job_id')
    def validate_job_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('job_id must be a valid UUID')
        return v
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Job duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return None
    
    @property
    def is_active(self) -> bool:
        """Whether the job is currently active"""
        return self.status in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.PAUSED]
    
    @property
    def is_finished(self) -> bool:
        """Whether the job has finished (successfully or not)"""
        return self.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
    
    @property
    def compression_ratio_formatted(self) -> str:
        """Formatted compression ratio"""
        if self.metrics and self.metrics.compression_ratio:
            return f"{self.metrics.compression_ratio:.2f}"
        return "N/A"
    
    @property
    def space_saved_formatted(self) -> str:
        """Formatted space savings"""
        if self.metrics and self.metrics.space_saved_percentage:
            return f"{self.metrics.space_saved_percentage:.1f}%"
        return "N/A"


class JobCreateRequest(BaseModel):
    """Request model for creating a compression job"""
    input_video_id: str = Field(..., description="ID of video to compress")
    settings: CompressionSettings = Field(..., description="Compression settings")
    priority: JobPriority = Field(default=JobPriority.NORMAL, description="Job priority")
    output_filename: Optional[str] = Field(None, description="Custom output filename")
    
    # Batch processing
    batch_id: Optional[str] = Field(None, description="Batch ID for grouping jobs")
    dependency_job_ids: List[str] = Field(default_factory=list, description="Jobs that must complete first")


class JobUpdateRequest(BaseModel):
    """Request model for updating a job"""
    priority: Optional[JobPriority] = Field(None, description="Updated priority")
    status: Optional[JobStatus] = Field(None, description="Updated status")
    
    @validator('status')
    def validate_status_transition(cls, v, values):
        # Define valid status transitions
        valid_transitions = {
            JobStatus.PENDING: [JobStatus.QUEUED, JobStatus.CANCELLED],
            JobStatus.QUEUED: [JobStatus.RUNNING, JobStatus.CANCELLED],
            JobStatus.RUNNING: [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.PAUSED],
            JobStatus.PAUSED: [JobStatus.RUNNING, JobStatus.CANCELLED],
            JobStatus.COMPLETED: [],  # Final state
            JobStatus.FAILED: [JobStatus.PENDING],  # Can retry
            JobStatus.CANCELLED: []  # Final state
        }
        # Note: This validation would need access to current status, which isn't available here
        # This should be handled in the business logic layer
        return v


class JobListResponse(BaseModel):
    """Response model for job list endpoints"""
    jobs: List[CompressionJob]
    total_count: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    page: int
    page_size: int


class JobQueueStatus(BaseModel):
    """Response model for job queue status"""
    total_jobs: int
    pending_jobs: int
    queued_jobs: int
    running_jobs: int
    paused_jobs: int
    active_workers: int
    estimated_queue_time_minutes: Optional[float]
    
    # Queue statistics
    average_processing_time_minutes: Optional[float]
    jobs_completed_today: int
    total_data_processed_gb: float


class JobSearchQuery(BaseModel):
    """Query parameters for job search"""
    status: Optional[List[JobStatus]] = Field(None, description="Filter by status")
    priority: Optional[List[JobPriority]] = Field(None, description="Filter by priority")
    created_after: Optional[datetime] = Field(None, description="Created after date")
    created_before: Optional[datetime] = Field(None, description="Created before date")
    input_video_id: Optional[str] = Field(None, description="Filter by input video ID")
    created_by: Optional[str] = Field(None, description="Filter by creator")
    batch_id: Optional[str] = Field(None, description="Filter by batch ID")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")
    page: int = Field(default=1, description="Page number")
    page_size: int = Field(default=20, description="Page size")


class BatchJobRequest(BaseModel):
    """Request model for batch job creation"""
    video_ids: List[str] = Field(..., description="List of video IDs to process")
    settings: CompressionSettings = Field(..., description="Compression settings for all videos")
    priority: JobPriority = Field(default=JobPriority.NORMAL, description="Priority for all jobs")
    batch_name: Optional[str] = Field(None, description="Name for this batch")
    parallel_jobs: int = Field(default=2, description="Number of jobs to run in parallel")
    
    @validator('video_ids')
    def validate_video_ids(cls, v):
        if not v:
            raise ValueError('At least one video ID must be provided')
        if len(v) > 100:
            raise ValueError('Cannot process more than 100 videos in a single batch')
        return v
    
    @validator('parallel_jobs')
    def validate_parallel_jobs(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Parallel jobs must be between 1 and 10')
        return v


class JobStatsResponse(BaseModel):
    """Response model for job statistics"""
    total_jobs: int
    jobs_by_status: Dict[str, int]
    jobs_by_priority: Dict[str, int]
    average_processing_time_hours: float
    total_data_processed_tb: float
    total_space_saved_tb: float
    average_compression_ratio: float
    jobs_today: int
    success_rate_percentage: float
    
    # Performance metrics
    peak_processing_speed_fps: float
    average_processing_speed_fps: float
    busiest_hour: int  # Hour of day with most job completions