# Mouse Video Compressor

A sophisticated web-based system for compressing research videos of mice with adaptive quality based on motion detection and activity analysis. The system automatically adjusts compression parameters during mouse activity periods and applies higher compression during inactive/sleep periods, optimizing storage while preserving behavioral data.

## 🎯 Features

### Core Functionality
- **Adaptive Video Compression**: Dynamic compression based on detected mouse activity levels
- **Motion Detection**: Advanced computer vision algorithms for accurate motion tracking
- **Activity Analysis**: Automated detection of sleep/wake cycles and activity patterns
- **Multiple Compression Profiles**: Conservative, Balanced, and Aggressive compression strategies
- **ROI-based Compression**: Focused compression around detected mouse regions
- **Real-time Processing**: Live progress monitoring with WebSocket updates

### Web Dashboard
- **Video Management**: Upload, organize, and manage research videos
- **Compression Queue**: Monitor and control compression jobs
- **Analytics Dashboard**: Visualize compression statistics and activity patterns
- **Batch Processing**: Process multiple videos simultaneously
- **Download Management**: Easy access to compressed videos and analysis results

### Research Features
- **Behavioral Insights**: Automated analysis of mouse behavior patterns
- **Circadian Pattern Detection**: Long-term activity rhythm analysis
- **Motion Timeline**: Detailed frame-by-frame activity tracking
- **Quality Preservation**: Maintains research data integrity during active periods
- **Metadata Preservation**: Retains video metadata and experimental information

## 🏗️ Architecture

```
mouse-video-compressor/
├── backend/                    # Python FastAPI backend
│   ├── compression/           # Core compression algorithms
│   ├── models/               # Data models and schemas
│   ├── utils/                # Utility functions
│   └── app.py               # Main application server
├── frontend/                  # React web interface
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/           # Custom React hooks
│   │   └── utils/           # Frontend utilities
│   └── public/              # Static assets
├── config/                   # Configuration files
├── scripts/                  # Setup and utility scripts
└── docker-compose.yml       # Container orchestration
```

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd mouse-video-compressor

# Run the setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Install system dependencies (FFmpeg, OpenCV, etc.)
- Set up Python virtual environment
- Install Python dependencies
- Set up Node.js environment
- Create necessary directories
- Configure the application

### Option 2: Docker Setup

```bash
# Clone the repository
git clone <repository-url>
cd mouse-video-compressor

# Create required directories
mkdir -p volumes/{videos/raw,videos/compressed,logs}

# Start with Docker Compose
docker-compose up --build
```

### Option 3: Manual Setup

#### Prerequisites
- Python 3.9+
- Node.js 16+
- FFmpeg with H.264 support
- OpenCV 4.5+
- Redis (optional, for job queue)

#### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run build
```

## 📖 Usage

### Starting the Application

#### Development Mode
```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
python app.py

# Terminal 2: Frontend
cd frontend
npm start
```

#### Production Mode
```bash
# Using Docker
docker-compose up

# Or manual
cd backend
source venv/bin/activate
python app.py
```

### Using the Web Interface

1. **Access the Dashboard**: Open http://localhost:3000
2. **Upload Videos**: Click "Upload Videos" and select your research videos
3. **Configure Compression**: Choose compression profile and settings
4. **Monitor Progress**: Watch real-time compression progress
5. **Download Results**: Access compressed videos and analysis reports

### API Usage

The system provides a RESTful API for programmatic access:

```python
import requests

# Upload a video
with open('mouse_video.mp4', 'rb') as f:
    response = requests.post('http://localhost:8000/api/videos/upload', 
                           files={'file': f})
video_id = response.json()['video_id']

# Start compression
compression_job = requests.post('http://localhost:8000/api/compress/start', 
                               json={
                                   'input_video_id': video_id,
                                   'settings': {
                                       'profile_type': 'balanced',
                                       'roi_compression_enabled': True
                                   }
                               })

# Monitor progress
job_id = compression_job.json()['job_id']
status = requests.get(f'http://localhost:8000/api/compress/{job_id}/status')
```

## ⚙️ Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Server Configuration
HOST=localhost
PORT=8000
DEBUG=true

# File Paths
VIDEO_INPUT_DIR=./videos/raw
VIDEO_OUTPUT_DIR=./videos/compressed
LOG_DIR=./logs

# FFmpeg Configuration
FFMPEG_PATH=ffmpeg
MAX_CONCURRENT_JOBS=2

# Motion Detection
MOTION_THRESHOLD=0.02
BACKGROUND_LEARNING_RATE=0.001
MIN_INACTIVE_DURATION=30
```

### Compression Profiles

Edit `config/compression_settings.json` to customize compression profiles:

```json
{
  "balanced": {
    "high_activity": {
      "crf": 21,
      "fps": 25,
      "preset": "medium"
    },
    "inactive": {
      "crf": 28,
      "fps": 10,
      "preset": "fast"
    }
  }
}
```

### Motion Detection Settings

Modify `config/motion_detection_config.json` for motion detection parameters:

```json
{
  "detection_parameters": {
    "motion_threshold": 0.02,
    "background_learning_rate": 0.001,
    "gaussian_blur_kernel": 21
  }
}
```

## 🧪 Testing

### Run Test Suite
```bash
# Automated testing
python scripts/test_compression.py

# With custom video
python scripts/test_compression.py --input your_video.mp4

# Performance benchmark
python scripts/test_compression.py --benchmark --iterations 5
```

### Manual Testing
```bash
# Create test video and run all tests
python scripts/test_compression.py --create-test-video

# Test specific components
python -m pytest tests/ -v
```

## 📊 Compression Profiles

### Conservative (Research Priority)
- **Use Case**: High-value research data, detailed behavioral analysis
- **Active Periods**: CRF 18-20, 25-30 fps, high quality
- **Inactive Periods**: CRF 23-25, 15-20 fps, good quality
- **Expected Compression**: 40-50% size reduction
- **Quality**: Excellent preservation of behavioral details

### Balanced (Default)
- **Use Case**: General research use, good quality-size balance
- **Active Periods**: CRF 21-24, 20-25 fps, good quality
- **Inactive Periods**: CRF 27-28, 10-15 fps, moderate quality
- **Expected Compression**: 60-70% size reduction
- **Quality**: Good preservation with significant space savings

### Aggressive (Storage Priority)
- **Use Case**: Long-term storage, preliminary screening
- **Active Periods**: CRF 23-26, 15-20 fps, moderate quality
- **Inactive Periods**: CRF 30-32, 5-10 fps, high compression
- **Expected Compression**: 75-85% size reduction
- **Quality**: Acceptable for general analysis, maximum space savings

## 🔧 Advanced Configuration

### Custom Compression Profiles

Create custom profiles by extending the configuration:

```json
{
  "custom_profile_name": {
    "name": "Custom Profile",
    "description": "Tailored for specific research needs",
    "expected_compression_ratio": 0.4,
    "activity_settings": {
      "high_activity": {
        "crf": 19,
        "fps": 30,
        "preset": "slow",
        "profile": "high"
      }
    }
  }
}
```

### Motion Detection Tuning

Fine-tune motion detection for your specific setup:

```json
{
  "detection_parameters": {
    "motion_threshold": 0.015,        // Lower = more sensitive
    "background_learning_rate": 0.001, // Lower = more stable background
    "min_inactive_duration": 60       // Seconds required for sleep detection
  }
}
```

### Performance Optimization

#### Hardware Acceleration
```bash
# Enable GPU acceleration (if available)
export OPENCV_FFMPEG_CAPTURE_OPTIONS="hwaccel;cuda"
```

#### Processing Optimization
```json
{
  "performance_settings": {
    "max_concurrent_jobs": 4,      // Adjust based on CPU cores
    "thread_count": 0,             // 0 = auto-detect
    "memory_limit_gb": 8           // RAM limit per job
  }
}
```

## 📈 Monitoring and Analytics

### System Metrics
- Processing speed (frames per second)
- Compression ratios achieved
- Storage space saved
- Queue processing times
- Error rates and types

### Research Analytics
- Activity pattern analysis
- Circadian rhythm detection
- Sleep/wake cycle quantification
- Motion intensity distributions
- Behavioral trend analysis

### Log Analysis
```bash
# View recent logs
tail -f logs/mouse_video_compressor.log

# Search for errors
grep ERROR logs/mouse_video_compressor.log

# Monitor compression jobs
grep "compression" logs/mouse_video_compressor.log
```

## 🐳 Docker Deployment

### Development Environment
```bash
docker-compose -f docker-compose.dev.yml up --build
```

### Production Deployment
```bash
# Production with monitoring
docker-compose --profile production --profile monitoring up -d
```

### Scaling
```bash
# Scale compression workers
docker-compose up --scale app=3
```

## 🔒 Security Considerations

### File Upload Security
- File type validation
- Size limits (configurable)
- Virus scanning (recommended)
- Secure file storage

### Network Security
- HTTPS recommended for production
- Authentication system (can be added)
- Rate limiting on API endpoints
- CORS configuration

### Data Privacy
- Local processing (no cloud dependency)
- Configurable data retention
- Secure deletion of temporary files
- Audit logging

## 🚨 Troubleshooting

### Common Issues

#### FFmpeg Not Found
```bash
# Install FFmpeg
./scripts/install_ffmpeg.sh

# Or manually
sudo apt-get install ffmpeg  # Ubuntu/Debian
brew install ffmpeg          # macOS
```

#### OpenCV Issues
```bash
# Reinstall OpenCV
pip uninstall opencv-python
pip install opencv-python==4.8.1.78
```

#### Memory Issues
```bash
# Reduce concurrent jobs
export MAX_CONCURRENT_JOBS=1

# Increase system memory or reduce video resolution
```

#### WebSocket Connection Issues
```bash
# Check firewall settings
# Verify port 8000 is accessible
# Check browser console for errors
```

### Debug Mode
```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

python app.py
```

### Performance Issues
```bash
# Monitor system resources
htop

# Check disk space
df -h

# Monitor compression progress
python scripts/test_compression.py --benchmark
```

## 📝 API Documentation

### Video Management
- `GET /api/videos` - List videos with filtering
- `POST /api/videos/upload` - Upload new video
- `GET /api/videos/{id}` - Get video details
- `DELETE /api/videos/{id}` - Delete video
- `POST /api/videos/{id}/analyze` - Start motion analysis

### Compression Jobs
- `POST /api/compress/start` - Start compression job
- `GET /api/compress/{job_id}/status` - Get job status
- `DELETE /api/compress/{job_id}` - Cancel job
- `GET /api/compress/queue` - Get queue status
- `POST /api/compress/batch` - Batch compression

### Configuration
- `GET /api/settings/profiles` - Get compression profiles
- `GET /api/settings/profiles/{video_id}/recommendations` - Get recommendations
- `PUT /api/settings/motion-detection` - Update motion settings

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Code Style
- Python: Follow PEP 8
- JavaScript: Use ESLint configuration
- Comments: Document complex algorithms
- Tests: Maintain >90% coverage

### Adding New Features
1. Update models if needed
2. Implement backend API endpoints
3. Add frontend components
4. Write comprehensive tests
5. Update documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenCV community for computer vision algorithms
- FFmpeg project for video processing capabilities
- React and FastAPI communities for web frameworks
- Research community for feature requirements and testing

## 📞 Support

### Getting Help
- Check the troubleshooting section
- Review existing issues on GitHub
- Run the test suite for diagnostics
- Enable debug logging for detailed information

### Reporting Issues
When reporting issues, please include:
- Operating system and version
- Python and Node.js versions
- Error messages and logs
- Steps to reproduce
- Sample video (if applicable)

### Feature Requests
- Describe the use case
- Explain the expected behavior
- Provide examples if possible
- Consider contributing the implementation

---

**Mouse Video Compressor** - Optimizing research video storage while preserving behavioral data integrity.

For more information, visit our [documentation](docs/) or check the [examples](examples/) directory.