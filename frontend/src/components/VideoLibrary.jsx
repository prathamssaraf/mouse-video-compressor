import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Typography,
  Button,
  IconButton,
  TextField,
  MenuItem,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Fab,
  Tooltip,
  LinearProgress,
  Menu,
  ListItemIcon,
  ListItemText,
  Divider,
  Alert,
  Pagination
} from '@mui/material';
import {
  Add as AddIcon,
  Search as SearchIcon,
  FilterList as FilterIcon,
  ViewList as ViewListIcon,
  ViewModule as ViewModuleIcon,
  MoreVert as MoreVertIcon,
  PlayArrow as PlayIcon,
  Archive as CompressIcon,
  Analytics as AnalyticsIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  CloudUpload as UploadIcon
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

// Import hooks and utilities
import { useVideoProcessing } from '../hooks/useVideoProcessing';
import { useNotifications } from '../hooks/useNotifications';
import { formatFileSize, formatDuration, formatRelativeTime, getStatusColor } from '../utils/formatters';

const VideoLibrary = ({ onStatsUpdate }) => {
  const [viewMode, setViewMode] = useState('grid'); // 'grid' or 'list'
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFormat, setSelectedFormat] = useState('all');
  const [selectedActivity, setSelectedActivity] = useState('all');
  const [sortBy, setSortBy] = useState('uploaded_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedVideos, setSelectedVideos] = useState([]);
  const [videoMenuAnchor, setVideoMenuAnchor] = useState(null);
  const [selectedVideoForMenu, setSelectedVideoForMenu] = useState(null);
  
  // Hooks
  const {
    videos,
    loading,
    error,
    uploadProgress,
    analysisProgress,
    compressionProgress,
    loadVideos,
    uploadVideo,
    analyzeVideo,
    compressVideo,
    deleteVideo,
    clearProgress
  } = useVideoProcessing();
  
  const { notifySuccess, notifyError, notifyVideoUploaded } = useNotifications();

  // Load videos on component mount and when filters change
  useEffect(() => {
    handleSearch();
  }, [searchQuery, selectedFormat, selectedActivity, sortBy, sortOrder, page]);

  const handleSearch = useCallback(async () => {
    try {
      const searchParams = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder
      };
      
      if (searchQuery) {
        searchParams.query = searchQuery;
      }
      
      if (selectedFormat !== 'all') {
        searchParams.format = selectedFormat;
      }
      
      if (selectedActivity !== 'all') {
        searchParams.activity_level = selectedActivity;
      }
      
      const result = await loadVideos(searchParams);
      
      // Update parent component with stats
      if (onStatsUpdate && result.total_count !== undefined) {
        onStatsUpdate(prev => ({ ...prev, total_videos: result.total_count }));
      }
      
    } catch (err) {
      notifyError(`Failed to load videos: ${err.message}`);
    }
  }, [searchQuery, selectedFormat, selectedActivity, sortBy, sortOrder, page, pageSize, loadVideos, onStatsUpdate, notifyError]);

  // File upload handling
  const onDrop = useCallback(async (acceptedFiles) => {
    for (const file of acceptedFiles) {
      try {
        const result = await uploadVideo(file, {
          auto_analyze: true
        });
        
        notifyVideoUploaded(file.name, result.video_id);
      } catch (err) {
        notifyError(`Failed to upload ${file.name}: ${err.message}`);
      }
    }
    
    setUploadDialogOpen(false);
  }, [uploadVideo, notifyVideoUploaded, notifyError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.wmv', '.mkv']
    },
    multiple: true
  });

  // Video actions
  const handleVideoAction = useCallback(async (action, videoId) => {
    try {
      switch (action) {
        case 'analyze':
          await analyzeVideo(videoId);
          notifySuccess('Video analysis started');
          break;
        
        case 'compress':
          // This would open compression settings dialog
          console.log('Open compression dialog for:', videoId);
          break;
        
        case 'download':
          // This would trigger download
          console.log('Download video:', videoId);
          break;
        
        case 'delete':
          if (window.confirm('Are you sure you want to delete this video?')) {
            await deleteVideo(videoId);
            notifySuccess('Video deleted successfully');
            handleSearch(); // Refresh list
          }
          break;
        
        default:
          console.log('Unknown action:', action);
      }
    } catch (err) {
      notifyError(`Failed to ${action} video: ${err.message}`);
    }
    
    setVideoMenuAnchor(null);
    setSelectedVideoForMenu(null);
  }, [analyzeVideo, deleteVideo, notifySuccess, notifyError, handleSearch]);

  // Menu handlers
  const handleVideoMenuOpen = (event, video) => {
    event.stopPropagation();
    setVideoMenuAnchor(event.currentTarget);
    setSelectedVideoForMenu(video);
  };

  const handleVideoMenuClose = () => {
    setVideoMenuAnchor(null);
    setSelectedVideoForMenu(null);
  };

  // Progress helpers
  const getVideoProgress = (videoId) => {
    if (uploadProgress[videoId]) return uploadProgress[videoId];
    if (analysisProgress[videoId]) return analysisProgress[videoId];
    if (compressionProgress[videoId]) return compressionProgress[videoId];
    return null;
  };

  const getProgressColor = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'error': return 'error';
      case 'running': return 'primary';
      default: return 'primary';
    }
  };

  // Video card component
  const VideoCard = ({ video, progress }) => (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardMedia
        component="img"
        height="140"
        image={`/api/videos/${video.id}/preview`}
        alt={video.filename}
        sx={{ objectFit: 'cover', backgroundColor: '#f5f5f5' }}
      />
      
      <CardContent sx={{ flexGrow: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
          <Typography variant="h6" component="h3" noWrap sx={{ flexGrow: 1, mr: 1 }}>
            {video.filename}
          </Typography>
          <IconButton
            size="small"
            onClick={(e) => handleVideoMenuOpen(e, video)}
          >
            <MoreVertIcon />
          </IconButton>
        </Box>
        
        <Typography variant="body2" color="textSecondary" gutterBottom>
          {formatFileSize(video.file_size_bytes)} • {formatDuration(video.metadata?.duration)}
        </Typography>
        
        <Typography variant="body2" color="textSecondary" gutterBottom>
          {formatRelativeTime(video.uploaded_at)}
        </Typography>
        
        {video.tags && video.tags.length > 0 && (
          <Box mt={1} mb={1}>
            {video.tags.slice(0, 2).map((tag) => (
              <Chip
                key={tag}
                label={tag}
                size="small"
                variant="outlined"
                sx={{ mr: 0.5, mb: 0.5 }}
              />
            ))}
            {video.tags.length > 2 && (
              <Chip
                label={`+${video.tags.length - 2}`}
                size="small"
                variant="outlined"
                sx={{ mr: 0.5, mb: 0.5 }}
              />
            )}
          </Box>
        )}
        
        {video.motion_analysis && (
          <Box display="flex" alignItems="center" mt={1}>
            <Typography variant="caption" color="textSecondary">
              Activity: {video.activity_level_description}
            </Typography>
            <Chip
              label="Analyzed"
              size="small"
              color="success"
              variant="outlined"
              sx={{ ml: 1 }}
            />
          </Box>
        )}
        
        {progress && (
          <Box mt={1}>
            <Typography variant="caption" color="textSecondary">
              {progress.status === 'running' ? `${progress.stage}: ${progress.progress?.toFixed(1)}%` : progress.status}
            </Typography>
            <LinearProgress
              variant="determinate"
              value={progress.progress || 0}
              color={getProgressColor(progress.status)}
              sx={{ mt: 0.5 }}
            />
          </Box>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Video Library
        </Typography>
        
        <Box display="flex" alignItems="center" gap={1}>
          <Tooltip title="List View">
            <IconButton
              onClick={() => setViewMode('list')}
              color={viewMode === 'list' ? 'primary' : 'default'}
            >
              <ViewListIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Grid View">
            <IconButton
              onClick={() => setViewMode('grid')}
              color={viewMode === 'grid' ? 'primary' : 'default'}
            >
              <ViewModuleIcon />
            </IconButton>
          </Tooltip>
          
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Upload Videos
          </Button>
        </Box>
      </Box>

      {/* Search and Filters */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} md={4}>
          <TextField
            fullWidth
            placeholder="Search videos..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
            }}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={2}>
          <TextField
            fullWidth
            select
            label="Format"
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
          >
            <MenuItem value="all">All Formats</MenuItem>
            <MenuItem value="mp4">MP4</MenuItem>
            <MenuItem value="avi">AVI</MenuItem>
            <MenuItem value="mov">MOV</MenuItem>
            <MenuItem value="wmv">WMV</MenuItem>
            <MenuItem value="mkv">MKV</MenuItem>
          </TextField>
        </Grid>
        
        <Grid item xs={12} sm={6} md={2}>
          <TextField
            fullWidth
            select
            label="Activity"
            value={selectedActivity}
            onChange={(e) => setSelectedActivity(e.target.value)}
          >
            <MenuItem value="all">All Levels</MenuItem>
            <MenuItem value="Very Active">Very Active</MenuItem>
            <MenuItem value="Active">Active</MenuItem>
            <MenuItem value="Moderate">Moderate</MenuItem>
            <MenuItem value="Low Activity">Low Activity</MenuItem>
            <MenuItem value="Minimal Activity">Minimal</MenuItem>
          </TextField>
        </Grid>
        
        <Grid item xs={12} sm={6} md={2}>
          <TextField
            fullWidth
            select
            label="Sort By"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <MenuItem value="uploaded_at">Upload Date</MenuItem>
            <MenuItem value="filename">Name</MenuItem>
            <MenuItem value="size">File Size</MenuItem>
            <MenuItem value="duration">Duration</MenuItem>
          </TextField>
        </Grid>
        
        <Grid item xs={12} sm={6} md={2}>
          <TextField
            fullWidth
            select
            label="Order"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value)}
          >
            <MenuItem value="desc">Descending</MenuItem>
            <MenuItem value="asc">Ascending</MenuItem>
          </TextField>
        </Grid>
      </Grid>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Box display="flex" justifyContent="center" py={4}>
          <LinearProgress sx={{ width: '100%' }} />
        </Box>
      )}

      {/* Video Grid/List */}
      {!loading && videos.length === 0 ? (
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          py={8}
          textAlign="center"
        >
          <Typography variant="h6" color="textSecondary" gutterBottom>
            No videos found
          </Typography>
          <Typography variant="body2" color="textSecondary" mb={3}>
            Upload some videos to get started with compression and analysis
          </Typography>
          <Button
            variant="contained"
            startIcon={<UploadIcon />}
            onClick={() => setUploadDialogOpen(true)}
          >
            Upload Your First Video
          </Button>
        </Box>
      ) : (
        <>
          <Grid container spacing={3}>
            {videos.map((video) => (
              <Grid item xs={12} sm={6} md={4} lg={3} key={video.id}>
                <VideoCard
                  video={video}
                  progress={getVideoProgress(video.id)}
                />
              </Grid>
            ))}
          </Grid>
          
          {/* Pagination */}
          <Box display="flex" justifyContent="center" mt={4}>
            <Pagination
              count={Math.ceil(videos.length / pageSize)}
              page={page}
              onChange={(e, newPage) => setPage(newPage)}
              color="primary"
            />
          </Box>
        </>
      )}

      {/* Video Context Menu */}
      <Menu
        anchorEl={videoMenuAnchor}
        open={Boolean(videoMenuAnchor)}
        onClose={handleVideoMenuClose}
      >
        <MenuItem onClick={() => handleVideoAction('analyze', selectedVideoForMenu?.id)}>
          <ListItemIcon>
            <AnalyticsIcon />
          </ListItemIcon>
          <ListItemText>Analyze Motion</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={() => handleVideoAction('compress', selectedVideoForMenu?.id)}>
          <ListItemIcon>
            <CompressIcon />
          </ListItemIcon>
          <ListItemText>Compress Video</ListItemText>
        </MenuItem>
        
        <Divider />
        
        <MenuItem onClick={() => handleVideoAction('download', selectedVideoForMenu?.id)}>
          <ListItemIcon>
            <DownloadIcon />
          </ListItemIcon>
          <ListItemText>Download</ListItemText>
        </MenuItem>
        
        <MenuItem onClick={() => handleVideoAction('delete', selectedVideoForMenu?.id)}>
          <ListItemIcon>
            <DeleteIcon color="error" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>

      {/* Upload Dialog */}
      <Dialog
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Upload Videos</DialogTitle>
        <DialogContent>
          <Box
            {...getRootProps()}
            sx={{
              border: '2px dashed',
              borderColor: isDragActive ? 'primary.main' : 'grey.300',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              backgroundColor: isDragActive ? 'action.hover' : 'transparent',
              '&:hover': {
                backgroundColor: 'action.hover'
              }
            }}
          >
            <input {...getInputProps()} />
            <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              {isDragActive ? 'Drop the videos here...' : 'Drag & drop videos here, or click to select'}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Supported formats: MP4, AVI, MOV, WMV, MKV
            </Typography>
          </Box>
          
          {/* Upload Progress */}
          {Object.keys(uploadProgress).length > 0 && (
            <Box mt={3}>
              <Typography variant="h6" gutterBottom>
                Upload Progress
              </Typography>
              {Object.entries(uploadProgress).map(([uploadId, progress]) => (
                <Box key={uploadId} mb={2}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="body2" noWrap sx={{ flexGrow: 1, mr: 2 }}>
                      {progress.filename}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      {progress.status === 'uploading' ? `${progress.progress}%` : progress.status}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={progress.progress}
                    color={getProgressColor(progress.status)}
                  />
                </Box>
              ))}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default VideoLibrary;