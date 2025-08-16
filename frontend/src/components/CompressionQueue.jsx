import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Chip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Grid,
  Alert,
  Tooltip
} from '@mui/material';
import {
  Pause as PauseIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  Info as InfoIcon
} from '@mui/icons-material';

import { api } from '../utils/api';
import { formatFileSize, formatDuration, formatRelativeTime, getStatusColor } from '../utils/formatters';

const CompressionQueue = ({ onJobsUpdate }) => {
  const [jobs, setJobs] = useState([]);
  const [queueStats, setQueueStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);

  useEffect(() => {
    loadQueueData();
    
    // Set up polling for real-time updates
    const interval = setInterval(loadQueueData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadQueueData = async () => {
    try {
      // Load jobs and queue statistics
      const [jobsResponse, queueResponse] = await Promise.all([
        api.get('/api/compress/jobs', { params: { page_size: 50 } }),
        api.get('/api/compress/queue')
      ]);
      
      setJobs(jobsResponse.data.jobs || []);
      setQueueStats(queueResponse.data);
      
      // Update parent component
      if (onJobsUpdate) {
        onJobsUpdate(queueResponse.data.running_jobs || 0);
      }
      
    } catch (error) {
      console.error('Failed to load queue data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleJobAction = async (action, jobId) => {
    try {
      switch (action) {
        case 'cancel':
          await api.delete(`/api/compress/${jobId}`);
          break;
        case 'details':
          const response = await api.get(`/api/compress/${jobId}/status`);
          setSelectedJob(response.data);
          setDetailsDialogOpen(true);
          return;
        default:
          console.log('Unknown action:', action);
      }
      
      // Refresh data after action
      await loadQueueData();
      
    } catch (error) {
      console.error(`Failed to ${action} job:`, error);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <PlayIcon color="primary" />;
      case 'pending':
        return <PauseIcon color="warning" />;
      case 'completed':
        return <PlayIcon color="success" />;
      case 'failed':
        return <StopIcon color="error" />;
      case 'cancelled':
        return <StopIcon color="default" />;
      default:
        return <InfoIcon />;
    }
  };

  const formatJobDuration = (job) => {
    if (job.completed_at && job.started_at) {
      const duration = new Date(job.completed_at) - new Date(job.started_at);
      return formatDuration(duration / 1000);
    }
    if (job.started_at) {
      const duration = new Date() - new Date(job.started_at);
      return formatDuration(duration / 1000);
    }
    return 'N/A';
  };

  const calculateCompressionRatio = (job) => {
    if (job.original_size_mb && job.compressed_size_mb) {
      const ratio = ((job.original_size_mb - job.compressed_size_mb) / job.original_size_mb) * 100;
      return `${ratio.toFixed(1)}%`;
    }
    return 'N/A';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <LinearProgress sx={{ width: '50%' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Compression Queue
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadQueueData}
        >
          Refresh
        </Button>
      </Box>

      {/* Queue Statistics */}
      {queueStats && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Total Jobs
                </Typography>
                <Typography variant="h5">
                  {queueStats.total_jobs}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Running Jobs
                </Typography>
                <Typography variant="h5" color="primary">
                  {queueStats.running_jobs}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Pending Jobs
                </Typography>
                <Typography variant="h5" color="warning.main">
                  {queueStats.pending_jobs}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="textSecondary" gutterBottom>
                  Est. Queue Time
                </Typography>
                <Typography variant="h5">
                  {queueStats.estimated_queue_time_minutes 
                    ? `${Math.ceil(queueStats.estimated_queue_time_minutes)}m`
                    : 'N/A'
                  }
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Jobs Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Compression Jobs
          </Typography>
          
          {jobs.length === 0 ? (
            <Alert severity="info">
              No compression jobs found. Start compressing videos to see them here.
            </Alert>
          ) : (
            <TableContainer component={Paper} elevation={0}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Status</TableCell>
                    <TableCell>Job ID</TableCell>
                    <TableCell>Video</TableCell>
                    <TableCell>Profile</TableCell>
                    <TableCell>Progress</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Compression</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {jobs.map((job) => (
                    <TableRow key={job.job_id}>
                      <TableCell>
                        <Box display="flex" alignItems="center">
                          {getStatusIcon(job.status)}
                          <Chip
                            label={job.status}
                            size="small"
                            color={getStatusColor(job.status)}
                            sx={{ ml: 1 }}
                          />
                        </Box>
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {job.job_id.substring(0, 8)}...
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2" noWrap>
                          Video {job.input_video_id?.substring(0, 8)}...
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Chip
                          label={job.settings?.profile_type || 'Unknown'}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      
                      <TableCell>
                        <Box width={100}>
                          {job.status === 'running' && job.progress ? (
                            <>
                              <LinearProgress
                                variant="determinate"
                                value={job.progress.percentage}
                                sx={{ mb: 0.5 }}
                              />
                              <Typography variant="caption">
                                {job.progress.percentage.toFixed(1)}%
                              </Typography>
                            </>
                          ) : (
                            <Typography variant="body2" color="textSecondary">
                              {job.status === 'completed' ? '100%' : 
                               job.status === 'failed' ? 'Failed' : 
                               job.status === 'cancelled' ? 'Cancelled' : '0%'}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2">
                          {formatJobDuration(job)}
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2">
                          {calculateCompressionRatio(job)}
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2">
                          {formatRelativeTime(job.created_at)}
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Box display="flex" gap={0.5}>
                          <Tooltip title="Job Details">
                            <IconButton
                              size="small"
                              onClick={() => handleJobAction('details', job.job_id)}
                            >
                              <InfoIcon />
                            </IconButton>
                          </Tooltip>
                          
                          {job.status === 'completed' && (
                            <Tooltip title="Download">
                              <IconButton
                                size="small"
                                onClick={() => handleJobAction('download', job.job_id)}
                              >
                                <DownloadIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                          
                          {job.status === 'running' && (
                            <Tooltip title="Cancel">
                              <IconButton
                                size="small"
                                onClick={() => handleJobAction('cancel', job.job_id)}
                              >
                                <StopIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                          
                          {['completed', 'failed', 'cancelled'].includes(job.status) && (
                            <Tooltip title="Remove">
                              <IconButton
                                size="small"
                                onClick={() => handleJobAction('remove', job.job_id)}
                              >
                                <DeleteIcon />
                              </IconButton>
                            </Tooltip>
                          )}
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Job Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Job Details</DialogTitle>
        <DialogContent>
          {selectedJob && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Job ID
                </Typography>
                <Typography variant="body2" fontFamily="monospace" gutterBottom>
                  {selectedJob.job_id}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Status
                </Typography>
                <Chip
                  label={selectedJob.status}
                  color={getStatusColor(selectedJob.status)}
                  size="small"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Profile
                </Typography>
                <Typography variant="body2" gutterBottom>
                  {selectedJob.settings?.profile_type || 'Unknown'}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Priority
                </Typography>
                <Typography variant="body2" gutterBottom>
                  {selectedJob.priority || 'Normal'}
                </Typography>
              </Grid>
              
              {selectedJob.progress && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    Current Progress
                  </Typography>
                  <Box mb={1}>
                    <Typography variant="body2" gutterBottom>
                      {selectedJob.progress.message || 'Processing...'}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={selectedJob.progress.percentage}
                      sx={{ mb: 1 }}
                    />
                    <Typography variant="caption">
                      {selectedJob.progress.percentage.toFixed(1)}% - Stage: {selectedJob.progress.current_stage}
                    </Typography>
                  </Box>
                </Grid>
              )}
              
              {selectedJob.original_size_mb && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Original Size
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    {formatFileSize(selectedJob.original_size_mb * 1024 * 1024)}
                  </Typography>
                </Grid>
              )}
              
              {selectedJob.compressed_size_mb && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Compressed Size
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    {formatFileSize(selectedJob.compressed_size_mb * 1024 * 1024)}
                  </Typography>
                </Grid>
              )}
              
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>
                  Created
                </Typography>
                <Typography variant="body2" gutterBottom>
                  {new Date(selectedJob.created_at).toLocaleString()}
                </Typography>
              </Grid>
              
              {selectedJob.started_at && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Started
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    {new Date(selectedJob.started_at).toLocaleString()}
                  </Typography>
                </Grid>
              )}
              
              {selectedJob.completed_at && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="subtitle2" gutterBottom>
                    Completed
                  </Typography>
                  <Typography variant="body2" gutterBottom>
                    {new Date(selectedJob.completed_at).toLocaleString()}
                  </Typography>
                </Grid>
              )}
              
              {selectedJob.error_info && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    Error Details
                  </Typography>
                  <Alert severity="error">
                    {selectedJob.error_info.error_message}
                  </Alert>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CompressionQueue;