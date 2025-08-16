import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  IconButton,
  Tooltip,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Paper,
  CircularProgress
} from '@mui/material';
import {
  VideoLibrary as VideoLibraryIcon,
  Archive as CompressIcon,
  Analytics as AnalyticsIcon,
  Refresh as RefreshIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  TrendingUp as TrendingUpIcon,
  Storage as StorageIcon,
  Speed as SpeedIcon
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

// Import chart components
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
  ArcElement
} from 'chart.js';

// Import API utility
import { api } from '../utils/api';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  ChartTooltip,
  Legend,
  ArcElement
);

const Dashboard = ({ globalStats, activeJobs, onRefresh }) => {
  const navigate = useNavigate();
  const [recentJobs, setRecentJobs] = useState([]);
  const [systemMetrics, setSystemMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load recent compression jobs
      const jobsResponse = await api.get('/api/compress/jobs', {
        params: { page: 1, page_size: 5, sort_by: 'created_at', sort_order: 'desc' }
      });
      setRecentJobs(jobsResponse.data.jobs || []);
      
      // Load system metrics (mock data for demo)
      setSystemMetrics({
        cpu_usage: 45,
        memory_usage: 62,
        disk_usage: 78,
        processing_speed: 2.3,
        queue_length: activeJobs
      });
      
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([loadDashboardData(), onRefresh()]);
    setRefreshing(false);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircleIcon color="success" />;
      case 'running':
        return <CircularProgress size={20} />;
      case 'failed':
        return <ErrorIcon color="error" />;
      case 'pending':
        return <ScheduleIcon color="warning" />;
      default:
        return <ScheduleIcon />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'primary';
      case 'failed':
        return 'error';
      case 'pending':
        return 'warning';
      default:
        return 'default';
    }
  };

  // Chart configurations
  const activityChartData = {
    labels: ['Very Active', 'Active', 'Moderate', 'Low Activity', 'Minimal Activity'],
    datasets: [
      {
        data: globalStats ? [
          globalStats.activity_distribution['Very Active'] || 0,
          globalStats.activity_distribution['Active'] || 0,
          globalStats.activity_distribution['Moderate'] || 0,
          globalStats.activity_distribution['Low Activity'] || 0,
          globalStats.activity_distribution['Minimal Activity'] || 0
        ] : [0, 0, 0, 0, 0],
        backgroundColor: [
          '#f44336',
          '#ff9800',
          '#ffeb3b',
          '#4caf50',
          '#2196f3'
        ],
        borderWidth: 2,
        borderColor: '#fff'
      }
    ]
  };

  const formatChartData = {
    labels: globalStats ? Object.keys(globalStats.format_distribution) : [],
    datasets: [
      {
        label: 'Video Count',
        data: globalStats ? Object.values(globalStats.format_distribution) : [],
        backgroundColor: [
          'rgba(54, 162, 235, 0.8)',
          'rgba(255, 99, 132, 0.8)',
          'rgba(255, 205, 86, 0.8)',
          'rgba(75, 192, 192, 0.8)',
          'rgba(153, 102, 255, 0.8)'
        ],
        borderColor: [
          'rgba(54, 162, 235, 1)',
          'rgba(255, 99, 132, 1)',
          'rgba(255, 205, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(153, 102, 255, 1)'
        ],
        borderWidth: 1
      }
    ]
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <CircularProgress size={60} />
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Dashboard
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </Box>

      {/* Statistics Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <VideoLibraryIcon color="primary" sx={{ fontSize: 40, mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Videos
                  </Typography>
                  <Typography variant="h4">
                    {globalStats?.total_videos || 0}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <StorageIcon color="primary" sx={{ fontSize: 40, mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Size
                  </Typography>
                  <Typography variant="h4">
                    {globalStats?.total_size_gb?.toFixed(1) || 0} GB
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <AnalyticsIcon color="primary" sx={{ fontSize: 40, mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Analyzed Videos
                  </Typography>
                  <Typography variant="h4">
                    {globalStats?.analyzed_videos || 0}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center">
                <SpeedIcon color="primary" sx={{ fontSize: 40, mr: 2 }} />
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Jobs
                  </Typography>
                  <Typography variant="h4" color={activeJobs > 0 ? 'primary' : 'inherit'}>
                    {activeJobs}
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts and Recent Activity */}
      <Grid container spacing={3}>
        {/* Activity Distribution Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Video Activity Distribution
              </Typography>
              <Box height={300} display="flex" justifyContent="center" alignItems="center">
                <Doughnut
                  data={activityChartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'bottom'
                      }
                    }
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Format Distribution Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Video Format Distribution
              </Typography>
              <Box height={300}>
                <Bar
                  data={formatChartData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        display: false
                      }
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        ticks: {
                          stepSize: 1
                        }
                      }
                    }
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Jobs */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  Recent Compression Jobs
                </Typography>
                <Button
                  size="small"
                  onClick={() => navigate('/queue')}
                  endIcon={<PlayIcon />}
                >
                  View All
                </Button>
              </Box>
              
              {recentJobs.length === 0 ? (
                <Typography color="textSecondary" align="center" py={3}>
                  No recent compression jobs
                </Typography>
              ) : (
                <List>
                  {recentJobs.map((job, index) => (
                    <React.Fragment key={job.job_id}>
                      <ListItem>
                        <ListItemIcon>
                          {getStatusIcon(job.status)}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center">
                              <Typography variant="body2" sx={{ mr: 1 }}>
                                Job {job.job_id.substring(0, 8)}...
                              </Typography>
                              <Chip
                                label={job.status}
                                size="small"
                                color={getStatusColor(job.status)}
                              />
                            </Box>
                          }
                          secondary={
                            <Box>
                              <Typography variant="caption" display="block">
                                {job.settings?.profile_type || 'Unknown profile'}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                {new Date(job.created_at).toLocaleString()}
                              </Typography>
                            </Box>
                          }
                        />
                        {job.status === 'running' && job.progress && (
                          <Box sx={{ width: 100, ml: 2 }}>
                            <LinearProgress
                              variant="determinate"
                              value={job.progress.percentage}
                              sx={{ mb: 0.5 }}
                            />
                            <Typography variant="caption" align="center" display="block">
                              {job.progress.percentage.toFixed(1)}%
                            </Typography>
                          </Box>
                        )}
                      </ListItem>
                      {index < recentJobs.length - 1 && <Divider />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* System Metrics */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Metrics
              </Typography>
              
              {systemMetrics && (
                <Box>
                  <Box mb={2}>
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2">CPU Usage</Typography>
                      <Typography variant="body2">{systemMetrics.cpu_usage}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemMetrics.cpu_usage}
                      color={systemMetrics.cpu_usage > 80 ? 'error' : 'primary'}
                    />
                  </Box>

                  <Box mb={2}>
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2">Memory Usage</Typography>
                      <Typography variant="body2">{systemMetrics.memory_usage}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemMetrics.memory_usage}
                      color={systemMetrics.memory_usage > 80 ? 'error' : 'primary'}
                    />
                  </Box>

                  <Box mb={2}>
                    <Box display="flex" justifyContent="space-between" mb={1}>
                      <Typography variant="body2">Disk Usage</Typography>
                      <Typography variant="body2">{systemMetrics.disk_usage}%</Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={systemMetrics.disk_usage}
                      color={systemMetrics.disk_usage > 80 ? 'warning' : 'primary'}
                    />
                  </Box>

                  <Divider sx={{ my: 2 }} />
                  
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="textSecondary">
                        Processing Speed
                      </Typography>
                      <Typography variant="h6">
                        {systemMetrics.processing_speed}x
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" color="textSecondary">
                        Queue Length
                      </Typography>
                      <Typography variant="h6">
                        {systemMetrics.queue_length}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Quick Actions */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Quick Actions
          </Typography>
          <Grid container spacing={2}>
            <Grid item>
              <Button
                variant="contained"
                startIcon={<VideoLibraryIcon />}
                onClick={() => navigate('/videos')}
              >
                Manage Videos
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="outlined"
                startIcon={<CompressIcon />}
                onClick={() => navigate('/queue')}
              >
                Compression Queue
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="outlined"
                startIcon={<TrendingUpIcon />}
                onClick={() => navigate('/analytics')}
              >
                View Analytics
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Dashboard;