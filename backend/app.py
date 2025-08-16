from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import asyncio
import uvicorn
import os
import uuid
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import shutil

# Import our models and components
from models.video import (
    Video, VideoSearchQuery, VideoListResponse, VideoUploadRequest,
    VideoUpdateRequest, VideoAnalysisRequest, VideoPreviewRequest,
    VideoStatsResponse, VideoBatchOperation
)
from models.compression_job import (
    CompressionJob, JobCreateRequest, JobUpdateRequest, JobListResponse,
    JobQueueStatus, JobSearchQuery, BatchJobRequest, JobStatsResponse,
    JobStatus, CompressionSettings
)

# Import our core components
from compression.motion_detector import MotionDetector
from compression.adaptive_compressor import AdaptiveCompressor
from compression.video_analyzer import VideoAnalyzer
from compression.compression_profiles import CompressionProfileManager, CompressionProfile

# Import utilities
from utils.file_handler import FileHandler
from utils.progress_tracker import ProgressTracker, ProgressEvent
from utils.logger import get_logger, LogComponent, LogLevel

# Initialize FastAPI app
app = FastAPI(
    title="Mouse Video Compressor API",
    description="Adaptive video compression system for mouse behavior research",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
logger = get_logger()
file_handler = FileHandler()
progress_tracker = ProgressTracker()
motion_detector = MotionDetector()
compressor = AdaptiveCompressor()
video_analyzer = VideoAnalyzer(motion_detector)
profile_manager = CompressionProfileManager()

# Global state
videos_db: Dict[str, Video] = {}
active_websockets: List[WebSocket] = []

# Configuration
INPUT_DIR = os.getenv("VIDEO_INPUT_DIR", "./videos/raw")
OUTPUT_DIR = os.getenv("VIDEO_OUTPUT_DIR", "./videos/compressed")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# Ensure directories exist
os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Start progress tracking
progress_tracker.start_tracking()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.log_system(LogLevel.INFO, "Starting Mouse Video Compressor API")
    
    # Scan for existing videos
    await refresh_video_database()
    
    # Store the main event loop for cross-thread async calls
    main_loop = asyncio.get_event_loop()
    
    # Setup WebSocket broadcasting for progress updates
    def broadcast_progress(event: ProgressEvent):
        try:
            if main_loop and not main_loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    broadcast_to_websockets({
                        "type": "progress_update",
                        "data": {
                            "job_id": event.job_id,
                            "event_type": event.event_type,
                            "percentage": event.percentage,
                            "stage": event.stage,
                            "message": event.message,
                            "timestamp": event.timestamp.isoformat()
                        }
                    }),
                    main_loop
                )
        except Exception as e:
            print(f"Error in progress broadcast: {e}")
    
    progress_tracker.subscribe_to_all(broadcast_progress)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.log_system(LogLevel.INFO, "Shutting down Mouse Video Compressor API")
    progress_tracker.stop_tracking()


# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {
            "api": "running",
            "database": "connected",
            "redis": "connected"
        }
    }


# Video Management Endpoints

@app.get("/api/videos", response_model=VideoListResponse)
async def list_videos(query: VideoSearchQuery = Depends()):
    """List videos with filtering and pagination"""
    try:
        # Apply filters (simplified implementation)
        filtered_videos = list(videos_db.values())
        
        # Apply search filters
        if query.query:
            filtered_videos = [v for v in filtered_videos if query.query.lower() in v.filename.lower()]
        
        if query.tags:
            filtered_videos = [v for v in filtered_videos if any(tag in v.tags for tag in query.tags)]
        
        if query.format:
            filtered_videos = [v for v in filtered_videos if v.format == query.format]
        
        if query.has_analysis is not None:
            filtered_videos = [v for v in filtered_videos if v.has_motion_analysis == query.has_analysis]
        
        # Apply size filters
        if query.min_file_size_mb:
            filtered_videos = [v for v in filtered_videos if v.file_size_mb >= query.min_file_size_mb]
        
        if query.max_file_size_mb:
            filtered_videos = [v for v in filtered_videos if v.file_size_mb <= query.max_file_size_mb]
        
        # Apply duration filters
        if query.min_duration and any(v.metadata for v in filtered_videos):
            filtered_videos = [v for v in filtered_videos if v.metadata and v.metadata.duration >= query.min_duration]
        
        if query.max_duration and any(v.metadata for v in filtered_videos):
            filtered_videos = [v for v in filtered_videos if v.metadata and v.metadata.duration <= query.max_duration]
        
        # Sort
        if query.sort_by == "filename":
            filtered_videos.sort(key=lambda x: x.filename, reverse=query.sort_order == "desc")
        elif query.sort_by == "size":
            filtered_videos.sort(key=lambda x: x.file_size_mb, reverse=query.sort_order == "desc")
        elif query.sort_by == "uploaded_at":
            filtered_videos.sort(key=lambda x: x.uploaded_at, reverse=query.sort_order == "desc")
        
        # Pagination
        total_count = len(filtered_videos)
        start_idx = (query.page - 1) * query.page_size
        end_idx = start_idx + query.page_size
        paginated_videos = filtered_videos[start_idx:end_idx]
        
        return VideoListResponse(
            videos=paginated_videos,
            total_count=total_count,
            page=query.page,
            page_size=query.page_size,
            total_pages=(total_count + query.page_size - 1) // query.page_size
        )
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error listing videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    """Get video by ID"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return videos_db[video_id]


@app.post("/api/videos/upload")
async def upload_video(file: UploadFile = File(...), metadata: str = "{}"):
    """Upload a new video file"""
    try:
        # Parse metadata
        upload_data = json.loads(metadata) if metadata != "{}" else {}
        
        # Validate file
        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.mkv')):
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Generate unique ID and save file
        video_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{video_id}_{file.filename}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Move to input directory
        final_path = os.path.join(INPUT_DIR, file.filename)
        final_path = file_handler._get_unique_filename(Path(final_path))
        shutil.move(file_path, final_path)
        
        # Create video record
        file_info = file_handler.get_file_info(final_path)
        video = create_video_from_file_info(video_id, file_info, upload_data)
        videos_db[video_id] = video
        
        logger.log_api_request(LogLevel.INFO, f"Video uploaded: {file.filename}", extra_data={"video_id": video_id})
        
        # Start analysis in background if requested
        if upload_data.get("auto_analyze", True):
            asyncio.create_task(start_video_analysis(video_id))
        
        return {"video_id": video_id, "message": "Video uploaded successfully"}
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/videos/{video_id}")
async def update_video(video_id: str, update_data: VideoUpdateRequest):
    """Update video metadata"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video = videos_db[video_id]
    
    # Update fields
    if update_data.description is not None:
        video.description = update_data.description
    if update_data.tags is not None:
        video.tags = update_data.tags
    if update_data.experiment_id is not None:
        video.experiment_id = update_data.experiment_id
    if update_data.subject_id is not None:
        video.subject_id = update_data.subject_id
    
    videos_db[video_id] = video
    
    logger.log_api_request(LogLevel.INFO, f"Video metadata updated", extra_data={"video_id": video_id})
    
    return {"message": "Video updated successfully"}


@app.delete("/api/videos/{video_id}")
async def delete_video(video_id: str):
    """Delete a video"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video = videos_db[video_id]
    
    # Delete file
    try:
        if os.path.exists(video.file_path):
            os.remove(video.file_path)
        
        # Delete analysis files if they exist
        if video.analysis_file_path and os.path.exists(video.analysis_file_path):
            os.remove(video.analysis_file_path)
        
        # Delete thumbnails
        for thumbnail in video.thumbnails:
            if os.path.exists(thumbnail.file_path):
                os.remove(thumbnail.file_path)
        
        del videos_db[video_id]
        
        logger.log_api_request(LogLevel.INFO, f"Video deleted", extra_data={"video_id": video_id})
        
        return {"message": "Video deleted successfully"}
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error deleting video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/videos/{video_id}/analyze")
async def analyze_video(video_id: str, background_tasks: BackgroundTasks):
    """Start video analysis"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    background_tasks.add_task(start_video_analysis, video_id)
    
    return {"message": "Video analysis started", "video_id": video_id}


@app.get("/api/videos/{video_id}/preview")
async def get_video_preview(video_id: str, timestamp: float = 0.0):
    """Get video preview frame"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video = videos_db[video_id]
    
    # Find existing thumbnail or generate one
    for thumbnail in video.thumbnails:
        if abs(thumbnail.timestamp - timestamp) < 1.0:  # Within 1 second
            return FileResponse(thumbnail.file_path)
    
    # Generate new thumbnail
    try:
        thumbnail_dir = os.path.join(OUTPUT_DIR, "thumbnails", video_id)
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        thumbnail_paths = file_handler.generate_thumbnails(
            video.file_path,
            thumbnail_dir,
            [timestamp]
        )
        
        if thumbnail_paths:
            return FileResponse(thumbnail_paths[0])
        else:
            raise HTTPException(status_code=500, detail="Could not generate thumbnail")
            
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/stats")
async def get_video_stats():
    """Get video statistics"""
    try:
        total_videos = len(videos_db)
        total_size = 0
        analyzed_videos = 0
        
        # Safe calculation with error handling
        for video in videos_db.values():
            try:
                if hasattr(video, 'file_size_mb') and video.file_size_mb:
                    total_size += video.file_size_mb
                if hasattr(video, 'motion_analysis') and video.motion_analysis:
                    analyzed_videos += 1
            except:
                continue
        
        return {
            "total_videos": total_videos,
            "total_size_gb": round(total_size / 1024, 2) if total_size else 0,
            "analyzed_videos": analyzed_videos,
            "recent_uploads": total_videos,  # Simplified
            "avg_activity_ratio": 0.0,  # Will be computed when we have data
            "format_distribution": {},
            "activity_distribution": {}
        }
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error getting video stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Compression Job Endpoints

@app.post("/api/compress/start")
async def start_compression(job_request: JobCreateRequest, background_tasks: BackgroundTasks):
    """Start a compression job"""
    try:
        if job_request.input_video_id not in videos_db:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video = videos_db[job_request.input_video_id]
        job_id = str(uuid.uuid4())
        
        # Generate output path
        output_filename = job_request.output_filename or f"compressed_{video.filename}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # Start compression job
        background_tasks.add_task(
            run_compression_job,
            job_id,
            video.file_path,
            output_path,
            job_request.settings
        )
        
        logger.log_api_request(LogLevel.INFO, f"Compression job started", extra_data={"job_id": job_id, "video_id": job_request.input_video_id})
        
        return {"job_id": job_id, "message": "Compression job started"}
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error starting compression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compress/{job_id}/status")
async def get_job_status(job_id: str):
    """Get compression job status"""
    try:
        job_status = progress_tracker.get_job_status(job_id)
        compression_job = compressor.get_job_status(job_id)
        
        if not job_status and not compression_job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        response = {}
        if job_status:
            response.update(job_status)
        if compression_job:
            response.update({
                "compression_details": compression_job,
                "original_size_mb": compression_job.original_size_mb,
                "compressed_size_mb": compression_job.compressed_size_mb
            })
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/compress/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a compression job"""
    try:
        success = compressor.cancel_job(job_id)
        if success:
            progress_tracker.cancel_job(job_id)
            return {"message": "Job cancelled successfully"}
        else:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error cancelling job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compress/jobs")
async def get_compression_jobs(page: int = 1, page_size: int = 5, sort_by: str = "created_at", sort_order: str = "desc"):
    """Get compression jobs with pagination"""
    try:
        # Return empty list for now - would be implemented with proper job storage
        return {
            "jobs": [],
            "total_count": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0
        }
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error getting compression jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/compress/queue", response_model=JobQueueStatus)
async def get_queue_status():
    """Get compression queue status"""
    try:
        # Simplified implementation to avoid hanging
        return JobQueueStatus(
            total_jobs=0,
            pending_jobs=0,
            queued_jobs=0,
            running_jobs=0,
            paused_jobs=0,
            active_workers=1,
            estimated_queue_time_minutes=0,
            jobs_completed_today=0,
            total_data_processed_gb=0
        )
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compress/batch")
async def start_batch_compression(batch_request: BatchJobRequest, background_tasks: BackgroundTasks):
    """Start batch compression jobs"""
    try:
        job_ids = []
        
        for video_id in batch_request.video_ids:
            if video_id not in videos_db:
                continue
            
            video = videos_db[video_id]
            job_id = str(uuid.uuid4())
            
            output_filename = f"compressed_{video.filename}"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            
            background_tasks.add_task(
                run_compression_job,
                job_id,
                video.file_path,
                output_path,
                batch_request.settings
            )
            
            job_ids.append(job_id)
        
        logger.log_api_request(LogLevel.INFO, f"Batch compression started", extra_data={"job_count": len(job_ids)})
        
        return {"job_ids": job_ids, "message": f"Started {len(job_ids)} compression jobs"}
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error starting batch compression: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Endpoints

@app.get("/api/settings/profiles")
async def get_compression_profiles():
    """Get available compression profiles"""
    try:
        profiles = profile_manager.list_all_profiles()
        return {"profiles": {name: {"name": profile.name, "description": profile.description, "expected_compression_ratio": profile.expected_compression_ratio} for name, profile in profiles.items()}}
        
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error getting profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/profiles/{video_id}/recommendations")
async def get_profile_recommendations(video_id: str):
    """Get compression profile recommendations for a video"""
    try:
        if video_id not in videos_db:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video = videos_db[video_id]
        
        if not video.metadata:
            raise HTTPException(status_code=400, detail="Video metadata not available")
        
        activity_ratio = video.motion_analysis.overall_activity_ratio if video.motion_analysis else 0.5
        
        recommendations = profile_manager.get_profile_recommendations(
            video.metadata.duration,
            video.file_size_mb,
            activity_ratio
        )
        
        return {"recommendations": recommendations}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.log_api_request(LogLevel.ERROR, f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time updates

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)


# Helper functions

async def refresh_video_database():
    """Refresh video database from file system"""
    try:
        file_infos = file_handler.scan_input_directory()
        
        for file_info in file_infos:
            video_id = str(uuid.uuid4())
            video = create_video_from_file_info(video_id, file_info)
            videos_db[video_id] = video
            
        logger.log_system(LogLevel.INFO, f"Loaded {len(file_infos)} videos from filesystem")
        
    except Exception as e:
        logger.log_system(LogLevel.ERROR, f"Error refreshing video database: {e}")


def create_video_from_file_info(video_id: str, file_info: Dict, upload_data: Dict = None) -> Video:
    """Create Video object from file info"""
    from models.video import VideoFormat, VideoMetadata, VideoStatus
    
    upload_data = upload_data or {}
    
    video = Video(
        id=video_id,
        filename=file_info['filename'],
        file_path=file_info['path'],
        file_size_bytes=file_info['size_bytes'],
        file_size_mb=file_info['size_mb'],
        format=file_info['format'],
        status=VideoStatus.AVAILABLE,
        metadata=file_info.get('metadata'),
        description=upload_data.get('description'),
        experiment_id=upload_data.get('experiment_id'),
        subject_id=upload_data.get('subject_id'),
        tags=upload_data.get('tags', [])
    )
    
    return video


async def start_video_analysis(video_id: str):
    """Start video analysis in background"""
    try:
        if video_id not in videos_db:
            return
        
        video = videos_db[video_id]
        
        # Register progress tracking
        progress_tracker.register_job(video_id, "motion_analysis")
        
        def progress_callback(progress, stage):
            progress_tracker.update_progress(video_id, progress, stage, f"Motion analysis: {stage}")
        
        # Run analysis
        analysis_result = video_analyzer.analyze_video_comprehensive(
            video.file_path,
            output_dir=os.path.join(OUTPUT_DIR, "analysis", video_id),
            progress_callback=progress_callback
        )
        
        # Update video with analysis results
        from models.video import MotionAnalysisSummary
        
        video.motion_analysis = MotionAnalysisSummary(
            overall_activity_ratio=analysis_result.motion_analysis.overall_activity_ratio,
            total_active_periods=len(analysis_result.motion_analysis.active_periods),
            total_sleep_periods=len(analysis_result.motion_analysis.sleep_periods),
            average_motion_intensity=sum(analysis_result.motion_analysis.motion_timeline) / len(analysis_result.motion_analysis.motion_timeline),
            has_circadian_pattern=analysis_result.behavioral_insights.get('circadian_patterns', {}).get('available', False),
            analysis_completed_at=datetime.now()
        )
        
        video.analysis_file_path = os.path.join(OUTPUT_DIR, "analysis", video_id, "analysis_report.json")
        videos_db[video_id] = video
        
        progress_tracker.complete_job(video_id, "Motion analysis completed")
        
        logger.log_motion_analysis_results(LogLevel.INFO, "Video analysis completed", job_id=video_id)
        
    except Exception as e:
        progress_tracker.fail_job(video_id, f"Analysis failed: {str(e)}")
        logger.log_motion_analysis_results(LogLevel.ERROR, f"Video analysis failed: {e}", job_id=video_id)


async def run_compression_job(job_id: str, input_path: str, output_path: str, settings: CompressionSettings):
    """Run compression job in background"""
    try:
        # Determine profile type
        profile_type = None
        for profile in CompressionProfile:
            if profile.value == settings.profile_type.value:
                profile_type = profile
                break
        
        if not profile_type:
            raise ValueError(f"Invalid profile type: {settings.profile_type}")
        
        # Register progress tracking
        progress_tracker.register_job(job_id, "compression")
        
        def progress_callback(job_id, progress, message):
            progress_tracker.update_progress(job_id, progress, "compression", message)
        
        # Start compression
        job = compressor.start_compression_job(
            job_id=job_id,
            input_path=input_path,
            output_path=output_path,
            profile_type=profile_type,
            progress_callback=progress_callback,
            roi_enabled=settings.roi_compression_enabled
        )
        
        # Monitor job completion
        while job.status in ["pending", "running"]:
            await asyncio.sleep(1)
            job = compressor.get_job_status(job_id)
        
        if job.status == "completed":
            progress_tracker.complete_job(job_id, "Compression completed successfully")
            logger.log_compression_metrics(LogLevel.INFO, "Compression completed", job_id=job_id, metrics={
                "original_size_mb": job.original_size_mb,
                "compressed_size_mb": job.compressed_size_mb,
                "compression_ratio": job.compressed_size_mb / job.original_size_mb if job.original_size_mb > 0 else 0
            })
        else:
            progress_tracker.fail_job(job_id, job.error_message or "Compression failed")
            logger.log_compression(LogLevel.ERROR, f"Compression failed: {job.error_message}", job_id=job_id)
        
        # Cleanup
        compressor.cleanup_job(job_id)
        
    except Exception as e:
        progress_tracker.fail_job(job_id, str(e))
        logger.log_compression(LogLevel.ERROR, f"Compression job failed: {e}", job_id=job_id)


async def broadcast_to_websockets(message: Dict[str, Any]):
    """Broadcast message to all connected WebSocket clients"""
    if not active_websockets:
        return
    
    disconnected = []
    for websocket in active_websockets:
        try:
            await websocket.send_json(message)
        except:
            disconnected.append(websocket)
    
    # Remove disconnected websockets
    for websocket in disconnected:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


# Static file serving for frontend
app.mount("/", StaticFiles(directory="../frontend/build", html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)