#!/usr/bin/env python3
"""
Test script for the Mouse Video Compressor system.
This script tests the compression functionality and validates the output.
"""

import sys
import os
import argparse
import tempfile
import shutil
from pathlib import Path
import json
import time

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from compression.motion_detector import MotionDetector
from compression.adaptive_compressor import AdaptiveCompressor
from compression.video_analyzer import VideoAnalyzer
from compression.compression_profiles import CompressionProfileManager, CompressionProfile
from utils.file_handler import FileHandler
from utils.logger import get_logger, LogComponent, LogLevel


def create_test_video(output_path, duration=10, width=640, height=480, fps=30):
    """Create a test video for compression testing."""
    import cv2
    import numpy as np
    
    print(f"Creating test video: {output_path}")
    
    # Define codec and create VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = duration * fps
    
    for frame_num in range(total_frames):
        # Create a frame with moving elements to simulate mouse activity
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add background gradient
        for y in range(height):
            frame[y, :] = [50 + y//10, 50 + y//10, 50 + y//10]
        
        # Add moving circle (simulating mouse)
        center_x = int(width * 0.3 + 0.4 * width * abs(np.sin(frame_num * 0.1)))
        center_y = int(height * 0.3 + 0.4 * height * abs(np.cos(frame_num * 0.05)))
        
        # Vary activity level throughout the video
        if frame_num < total_frames * 0.3:
            # High activity period
            radius = 20 + int(10 * np.sin(frame_num * 0.3))
            cv2.circle(frame, (center_x, center_y), radius, (255, 255, 255), -1)
            # Add some noise for more motion
            noise_x = int(5 * np.sin(frame_num * 0.5))
            noise_y = int(5 * np.cos(frame_num * 0.7))
            cv2.circle(frame, (center_x + noise_x, center_y + noise_y), 5, (200, 200, 200), -1)
            
        elif frame_num < total_frames * 0.7:
            # Low activity period (sleep simulation)
            radius = 15
            cv2.circle(frame, (center_x, center_y), radius, (128, 128, 128), -1)
            
        else:
            # Medium activity period
            radius = 18
            cv2.circle(frame, (center_x, center_y), radius, (180, 180, 180), -1)
            if frame_num % 10 < 5:  # Intermittent movement
                cv2.circle(frame, (center_x + 10, center_y + 10), 8, (220, 220, 220), -1)
        
        out.write(frame)
    
    out.release()
    print(f"Test video created: {output_path}")
    return output_path


def test_motion_detection(video_path, output_dir):
    """Test the motion detection functionality."""
    print("\n=== Testing Motion Detection ===")
    
    detector = MotionDetector()
    
    try:
        # Analyze the video
        result = detector.analyze_video(video_path, 
                                      progress_callback=lambda p, s: print(f"Progress: {p:.1f}% - {s}"))
        
        print(f"Motion analysis completed:")
        print(f"  Duration: {result.total_duration:.2f} seconds")
        print(f"  Total frames: {result.total_frames}")
        print(f"  FPS: {result.fps:.2f}")
        print(f"  Activity segments: {len(result.activity_segments)}")
        print(f"  Overall activity ratio: {result.overall_activity_ratio:.3f}")
        print(f"  Sleep periods: {len(result.sleep_periods)}")
        print(f"  Active periods: {len(result.active_periods)}")
        
        # Save results
        results_file = os.path.join(output_dir, "motion_analysis_results.json")
        detector.save_analysis_results(result, results_file)
        print(f"Results saved to: {results_file}")
        
        return result
        
    except Exception as e:
        print(f"Motion detection test failed: {e}")
        return None


def test_compression(video_path, motion_analysis, output_dir):
    """Test the adaptive compression functionality."""
    print("\n=== Testing Adaptive Compression ===")
    
    compressor = AdaptiveCompressor()
    profile_manager = CompressionProfileManager()
    
    results = {}
    
    # Test each compression profile
    for profile_type in [CompressionProfile.CONSERVATIVE, CompressionProfile.BALANCED, CompressionProfile.AGGRESSIVE]:
        print(f"\nTesting {profile_type.value} profile...")
        
        profile = profile_manager.get_profile(profile_type)
        output_file = os.path.join(output_dir, f"compressed_{profile_type.value}.mp4")
        
        job_id = f"test_{profile_type.value}_{int(time.time())}"
        
        try:
            start_time = time.time()
            
            # Start compression job
            job = compressor.start_compression_job(
                job_id=job_id,
                input_path=video_path,
                output_path=output_file,
                profile_type=profile_type,
                progress_callback=lambda jid, p, m: print(f"  Progress: {p:.1f}% - {m}"),
                roi_enabled=True
            )
            
            # Wait for completion
            while job.status in ["pending", "running"]:
                time.sleep(0.5)
                job = compressor.get_job_status(job_id)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if job.status == "completed":
                print(f"  ✅ Compression completed successfully")
                print(f"  Processing time: {processing_time:.2f} seconds")
                print(f"  Original size: {job.original_size_mb:.2f} MB")
                print(f"  Compressed size: {job.compressed_size_mb:.2f} MB")
                print(f"  Compression ratio: {(job.compressed_size_mb/job.original_size_mb)*100:.1f}%")
                print(f"  Space saved: {((job.original_size_mb-job.compressed_size_mb)/job.original_size_mb)*100:.1f}%")
                
                results[profile_type.value] = {
                    'status': 'success',
                    'processing_time': processing_time,
                    'original_size_mb': job.original_size_mb,
                    'compressed_size_mb': job.compressed_size_mb,
                    'compression_ratio': job.compressed_size_mb/job.original_size_mb,
                    'space_saved_percent': ((job.original_size_mb-job.compressed_size_mb)/job.original_size_mb)*100,
                    'output_file': output_file
                }
            else:
                print(f"  ❌ Compression failed: {job.error_message}")
                results[profile_type.value] = {
                    'status': 'failed',
                    'error': job.error_message
                }
            
            # Cleanup job
            compressor.cleanup_job(job_id)
            
        except Exception as e:
            print(f"  ❌ Compression test failed: {e}")
            results[profile_type.value] = {
                'status': 'error',
                'error': str(e)
            }
    
    # Save compression results
    results_file = os.path.join(output_dir, "compression_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nCompression results saved to: {results_file}")
    
    return results


def test_video_analyzer(video_path, output_dir):
    """Test the video analyzer functionality."""
    print("\n=== Testing Video Analyzer ===")
    
    analyzer = VideoAnalyzer()
    
    try:
        # Perform comprehensive analysis
        report = analyzer.analyze_video_comprehensive(
            video_path,
            output_dir=os.path.join(output_dir, "analysis"),
            generate_visualizations=True,
            progress_callback=lambda p, s: print(f"Analysis progress: {p:.1f}% - {s}")
        )
        
        print(f"Video analysis completed:")
        print(f"  File size: {report.file_size_mb:.2f} MB")
        print(f"  Duration: {report.duration_seconds:.2f} seconds")
        print(f"  Resolution: {report.resolution[0]}x{report.resolution[1]}")
        print(f"  FPS: {report.fps:.2f}")
        print(f"  Codec: {report.codec}")
        
        print(f"  Behavioral insights:")
        activity_dist = report.behavioral_insights['activity_distribution']
        print(f"    High activity: {activity_dist['high']:.1f}%")
        print(f"    Medium activity: {activity_dist['medium']:.1f}%")
        print(f"    Low activity: {activity_dist['low']:.1f}%")
        print(f"    Inactive: {activity_dist['inactive']:.1f}%")
        
        print(f"  Recommendations:")
        rec_profile = report.recommendations['profile']['recommended']
        rec_reason = report.recommendations['profile']['reason']
        print(f"    Recommended profile: {rec_profile}")
        print(f"    Reason: {rec_reason}")
        
        return report
        
    except Exception as e:
        print(f"Video analysis test failed: {e}")
        return None


def test_file_handler():
    """Test the file handler functionality."""
    print("\n=== Testing File Handler ===")
    
    file_handler = FileHandler()
    
    try:
        # Test directory scanning
        video_files = file_handler.scan_input_directory()
        print(f"Found {len(video_files)} video files in input directory")
        
        # Test available space
        space_info = file_handler.get_available_space(".")
        print(f"Available space: {space_info['available_gb']:.2f} GB")
        
        print("File handler test completed successfully")
        return True
        
    except Exception as e:
        print(f"File handler test failed: {e}")
        return False


def run_performance_benchmark(video_path, output_dir, iterations=3):
    """Run performance benchmark tests."""
    print(f"\n=== Performance Benchmark ({iterations} iterations) ===")
    
    compressor = AdaptiveCompressor()
    
    # Test balanced profile performance
    total_times = []
    
    for i in range(iterations):
        print(f"Iteration {i+1}/{iterations}")
        
        job_id = f"benchmark_{i}_{int(time.time())}"
        output_file = os.path.join(output_dir, f"benchmark_{i}.mp4")
        
        start_time = time.time()
        
        job = compressor.start_compression_job(
            job_id=job_id,
            input_path=video_path,
            output_path=output_file,
            profile_type=CompressionProfile.BALANCED,
            roi_enabled=True
        )
        
        # Wait for completion
        while job.status in ["pending", "running"]:
            time.sleep(0.1)
            job = compressor.get_job_status(job_id)
        
        end_time = time.time()
        processing_time = end_time - start_time
        total_times.append(processing_time)
        
        print(f"  Iteration {i+1} completed in {processing_time:.2f} seconds")
        
        compressor.cleanup_job(job_id)
        
        # Clean up output file
        if os.path.exists(output_file):
            os.remove(output_file)
    
    avg_time = sum(total_times) / len(total_times)
    min_time = min(total_times)
    max_time = max(total_times)
    
    print(f"\nPerformance Results:")
    print(f"  Average time: {avg_time:.2f} seconds")
    print(f"  Min time: {min_time:.2f} seconds")
    print(f"  Max time: {max_time:.2f} seconds")
    print(f"  Performance variation: {((max_time - min_time) / avg_time) * 100:.1f}%")
    
    return {
        'average_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'all_times': total_times
    }


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description='Test Mouse Video Compressor')
    parser.add_argument('--input', '-i', help='Input video file (optional, will create test video if not provided)')
    parser.add_argument('--output', '-o', default='./test_output', help='Output directory for test results')
    parser.add_argument('--benchmark', '-b', action='store_true', help='Run performance benchmark')
    parser.add_argument('--iterations', default=3, type=int, help='Number of benchmark iterations')
    parser.add_argument('--create-test-video', action='store_true', help='Create a test video for testing')
    
    args = parser.parse_args()
    
    # Setup logger
    logger = get_logger()
    logger.log_system(LogLevel.INFO, "Starting compression system tests")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🐭 Mouse Video Compressor Test Suite")
    print("===================================")
    
    # Determine input video
    if args.input and os.path.exists(args.input):
        video_path = args.input
        print(f"Using provided video: {video_path}")
    else:
        if args.create_test_video or not args.input:
            # Create test video
            video_path = os.path.join(output_dir, "test_video.mp4")
            create_test_video(video_path, duration=20)
        else:
            print(f"Error: Input video '{args.input}' not found")
            return 1
    
    # Run tests
    test_results = {
        'video_path': video_path,
        'timestamp': time.time(),
        'tests': {}
    }
    
    # Test file handler
    test_results['tests']['file_handler'] = test_file_handler()
    
    # Test motion detection
    motion_result = test_motion_detection(video_path, output_dir)
    test_results['tests']['motion_detection'] = motion_result is not None
    
    # Test video analyzer
    analysis_report = test_video_analyzer(video_path, output_dir)
    test_results['tests']['video_analyzer'] = analysis_report is not None
    
    # Test compression
    compression_results = test_compression(video_path, motion_result, output_dir)
    test_results['tests']['compression'] = compression_results
    
    # Run benchmark if requested
    if args.benchmark:
        benchmark_results = run_performance_benchmark(video_path, output_dir, args.iterations)
        test_results['benchmark'] = benchmark_results
    
    # Save test results
    results_file = os.path.join(output_dir, "test_results.json")
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    
    print(f"\n=== Test Summary ===")
    print(f"Test results saved to: {results_file}")
    
    # Count successful tests
    successful_tests = sum([
        test_results['tests']['file_handler'],
        test_results['tests']['motion_detection'],
        test_results['tests']['video_analyzer'],
        len([r for r in compression_results.values() if r.get('status') == 'success'])
    ])
    
    total_tests = 3 + len(compression_results)
    
    print(f"Successful tests: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Check the output for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())