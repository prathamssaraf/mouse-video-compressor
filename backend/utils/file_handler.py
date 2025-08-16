import os
import shutil
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
import tempfile
import json
from datetime import datetime
import cv2
import numpy as np
from PIL import Image

from models.video import Video, VideoFormat, VideoMetadata


class FileHandler:
    """
    Handles file operations for video processing system
    """
    
    def __init__(self, 
                 input_dir: str = "./videos/raw",
                 output_dir: str = "./videos/compressed",
                 temp_dir: str = "./temp",
                 max_file_size_gb: float = 10.0):
        
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.max_file_size_bytes = int(max_file_size_gb * 1024 * 1024 * 1024)
        
        # Supported video formats
        self.supported_formats = {
            '.mp4': VideoFormat.MP4,
            '.avi': VideoFormat.AVI,
            '.mov': VideoFormat.MOV,
            '.wmv': VideoFormat.WMV,
            '.mkv': VideoFormat.MKV
        }
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        for directory in [self.input_dir, self.output_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def scan_input_directory(self) -> List[Dict]:
        """
        Scan input directory for video files
        Returns list of file information dictionaries
        """
        video_files = []
        
        for file_path in self.input_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    file_info = self.get_file_info(file_path)
                    video_files.append(file_info)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
        
        return sorted(video_files, key=lambda x: x['modified_time'], reverse=True)
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict:
        """
        Get comprehensive file information
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stat = file_path.stat()
        
        file_info = {
            'path': str(file_path.absolute()),
            'filename': file_path.name,
            'extension': file_path.suffix.lower(),
            'size_bytes': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'created_time': datetime.fromtimestamp(stat.st_ctime),
            'modified_time': datetime.fromtimestamp(stat.st_mtime),
            'is_video': file_path.suffix.lower() in self.supported_formats,
            'format': self.supported_formats.get(file_path.suffix.lower()),
            'checksum': self.calculate_checksum(file_path)
        }
        
        # Get video metadata if it's a video file
        if file_info['is_video']:
            try:
                metadata = self.extract_video_metadata(file_path)
                file_info['metadata'] = metadata
            except Exception as e:
                file_info['metadata_error'] = str(e)
        
        return file_info
    
    def extract_video_metadata(self, file_path: Union[str, Path]) -> VideoMetadata:
        """
        Extract video metadata using OpenCV
        """
        file_path = str(file_path)
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {file_path}")
        
        try:
            # Extract metadata
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate duration
            duration = frame_count / fps if fps > 0 else 0
            
            # Get codec information
            fourcc = cap.get(cv2.CAP_PROP_FOURCC)
            codec = "".join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)]).strip()
            
            # Try to get bitrate (not always available in OpenCV)
            bitrate = None
            try:
                bitrate = int(cap.get(cv2.CAP_PROP_BITRATE))
            except:
                pass
            
            metadata = VideoMetadata(
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                codec=codec,
                bitrate=bitrate,
                frame_count=frame_count
            )
            
            return metadata
            
        finally:
            cap.release()
    
    def calculate_checksum(self, file_path: Union[str, Path], algorithm: str = "md5") -> str:
        """
        Calculate file checksum
        """
        hash_algo = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                hash_algo.update(chunk)
        
        return hash_algo.hexdigest()
    
    def validate_video_file(self, file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """
        Validate video file integrity and format
        Returns (is_valid, error_message)
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            return False, "File does not exist"
        
        # Check file size
        if file_path.stat().st_size == 0:
            return False, "File is empty"
        
        if file_path.stat().st_size > self.max_file_size_bytes:
            max_size_gb = self.max_file_size_bytes / (1024**3)
            return False, f"File size exceeds maximum allowed size of {max_size_gb}GB"
        
        # Check file extension
        if file_path.suffix.lower() not in self.supported_formats:
            return False, f"Unsupported file format: {file_path.suffix}"
        
        # Try to open with OpenCV
        cap = cv2.VideoCapture(str(file_path))
        
        if not cap.isOpened():
            return False, "Cannot open video file - file may be corrupted"
        
        try:
            # Check basic properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
                return False, "Invalid video properties detected"
            
            # Try to read first frame
            ret, frame = cap.read()
            if not ret or frame is None:
                return False, "Cannot read video frames"
            
            return True, None
            
        finally:
            cap.release()
    
    def move_file(self, source: Union[str, Path], destination: Union[str, Path], 
                  overwrite: bool = False) -> str:
        """
        Move file from source to destination
        Returns the final destination path
        """
        source = Path(source)
        destination = Path(destination)
        
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle filename conflicts
        if destination.exists() and not overwrite:
            destination = self._get_unique_filename(destination)
        
        shutil.move(str(source), str(destination))
        return str(destination)
    
    def copy_file(self, source: Union[str, Path], destination: Union[str, Path],
                  overwrite: bool = False) -> str:
        """
        Copy file from source to destination
        Returns the final destination path
        """
        source = Path(source)
        destination = Path(destination)
        
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        if destination.exists() and not overwrite:
            destination = self._get_unique_filename(destination)
        
        shutil.copy2(str(source), str(destination))
        return str(destination)
    
    def delete_file(self, file_path: Union[str, Path], secure: bool = False) -> bool:
        """
        Delete file
        If secure=True, overwrites file with random data before deletion
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False
        
        if secure:
            # Overwrite with random data
            file_size = file_path.stat().st_size
            with open(file_path, 'wb') as f:
                # Write random data in chunks
                chunk_size = 1024 * 1024  # 1MB chunks
                for _ in range(0, file_size, chunk_size):
                    chunk = min(chunk_size, file_size - f.tell())
                    f.write(os.urandom(chunk))
        
        file_path.unlink()
        return True
    
    def create_temp_file(self, suffix: str = "", prefix: str = "temp_", 
                        directory: Optional[str] = None) -> str:
        """
        Create temporary file and return path
        """
        temp_dir = directory or self.temp_dir
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=temp_dir)
        os.close(fd)  # Close the file descriptor
        
        return temp_path
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up temporary files older than specified age
        """
        current_time = datetime.now()
        
        for temp_file in self.temp_dir.glob("*"):
            if temp_file.is_file():
                file_age = current_time - datetime.fromtimestamp(temp_file.stat().st_mtime)
                if file_age.total_seconds() > max_age_hours * 3600:
                    try:
                        temp_file.unlink()
                    except Exception as e:
                        print(f"Failed to delete temp file {temp_file}: {e}")
    
    def get_available_space(self, directory: Union[str, Path]) -> Dict[str, int]:
        """
        Get available disk space for directory
        """
        directory = Path(directory)
        
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
        
        statvfs = os.statvfs(str(directory))
        
        return {
            'total_bytes': statvfs.f_frsize * statvfs.f_blocks,
            'available_bytes': statvfs.f_frsize * statvfs.f_bavail,
            'used_bytes': statvfs.f_frsize * (statvfs.f_blocks - statvfs.f_bavail),
            'total_gb': (statvfs.f_frsize * statvfs.f_blocks) / (1024**3),
            'available_gb': (statvfs.f_frsize * statvfs.f_bavail) / (1024**3),
            'used_gb': (statvfs.f_frsize * (statvfs.f_blocks - statvfs.f_bavail)) / (1024**3),
            'usage_percentage': ((statvfs.f_blocks - statvfs.f_bavail) / statvfs.f_blocks) * 100
        }
    
    def generate_thumbnails(self, video_path: Union[str, Path], 
                           output_dir: Union[str, Path],
                           timestamps: List[float],
                           size: Tuple[int, int] = (320, 240)) -> List[str]:
        """
        Generate thumbnail images from video at specified timestamps
        """
        video_path = str(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        thumbnail_paths = []
        
        try:
            for i, timestamp in enumerate(timestamps):
                # Set video position
                frame_number = int(timestamp * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Resize frame
                frame_resized = cv2.resize(frame, size)
                
                # Convert BGR to RGB for PIL
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                
                # Save as PNG
                thumbnail_filename = f"thumbnail_{i:03d}_{timestamp:.1f}s.png"
                thumbnail_path = output_dir / thumbnail_filename
                
                image = Image.fromarray(frame_rgb)
                image.save(thumbnail_path)
                
                thumbnail_paths.append(str(thumbnail_path))
        
        finally:
            cap.release()
        
        return thumbnail_paths
    
    def create_video_preview(self, video_path: Union[str, Path],
                           output_path: Union[str, Path],
                           duration_seconds: int = 10,
                           start_timestamp: float = 0) -> str:
        """
        Create a short preview video clip
        """
        import ffmpeg
        
        input_stream = ffmpeg.input(str(video_path), ss=start_timestamp, t=duration_seconds)
        output_stream = ffmpeg.output(
            input_stream,
            str(output_path),
            vcodec='libx264',
            acodec='aac',
            crf=23,
            preset='fast'
        )
        
        ffmpeg.run(output_stream, overwrite_output=True, quiet=True)
        return str(output_path)
    
    def get_directory_size(self, directory: Union[str, Path]) -> int:
        """
        Calculate total size of directory in bytes
        """
        directory = Path(directory)
        
        if not directory.exists():
            return 0
        
        total_size = 0
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    
    def organize_files_by_date(self, source_dir: Union[str, Path],
                              target_dir: Union[str, Path]) -> Dict[str, List[str]]:
        """
        Organize files into date-based subdirectories (YYYY/MM/DD)
        """
        source_dir = Path(source_dir)
        target_dir = Path(target_dir)
        
        organized_files = {}
        
        for file_path in source_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                # Get file creation date
                creation_time = datetime.fromtimestamp(file_path.stat().st_ctime)
                date_path = creation_time.strftime("%Y/%m/%d")
                
                # Create target directory
                target_subdir = target_dir / date_path
                target_subdir.mkdir(parents=True, exist_ok=True)
                
                # Move file
                target_file_path = target_subdir / file_path.name
                target_file_path = self._get_unique_filename(target_file_path)
                
                shutil.move(str(file_path), str(target_file_path))
                
                if date_path not in organized_files:
                    organized_files[date_path] = []
                organized_files[date_path].append(str(target_file_path))
        
        return organized_files
    
    def _get_unique_filename(self, file_path: Path) -> Path:
        """
        Get unique filename by appending counter if file exists
        """
        if not file_path.exists():
            return file_path
        
        base = file_path.stem
        suffix = file_path.suffix
        parent = file_path.parent
        
        counter = 1
        while True:
            new_name = f"{base}_{counter}{suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def backup_file(self, file_path: Union[str, Path], 
                   backup_dir: Optional[Union[str, Path]] = None) -> str:
        """
        Create backup copy of file with timestamp
        """
        file_path = Path(file_path)
        
        if backup_dir is None:
            backup_dir = file_path.parent / "backups"
        else:
            backup_dir = Path(backup_dir)
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_filename
        
        shutil.copy2(str(file_path), str(backup_path))
        return str(backup_path)
    
    def get_file_type_stats(self, directory: Union[str, Path]) -> Dict[str, Dict]:
        """
        Get statistics about file types in directory
        """
        directory = Path(directory)
        stats = {}
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                extension = file_path.suffix.lower()
                
                if extension not in stats:
                    stats[extension] = {
                        'count': 0,
                        'total_size_bytes': 0,
                        'total_size_mb': 0
                    }
                
                file_size = file_path.stat().st_size
                stats[extension]['count'] += 1
                stats[extension]['total_size_bytes'] += file_size
                stats[extension]['total_size_mb'] = stats[extension]['total_size_bytes'] / (1024 * 1024)
        
        return stats