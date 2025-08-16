import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Menu,
  MenuItem,
  Badge,
  Tooltip,
  CircularProgress,
  Backdrop
} from '@mui/material';
import {
  VideoLibrary as VideoLibraryIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Info as InfoIcon,
  Menu as MenuIcon
} from '@mui/icons-material';

// Import components
import Dashboard from './components/Dashboard';
import VideoLibrary from './components/VideoLibrary';
import CompressionQueue from './components/CompressionQueue';
import Settings from './components/Settings';
import Analytics from './components/Analytics';

// Import hooks
import { useWebSocket } from './hooks/useWebSocket';
import { useNotifications } from './hooks/useNotifications';

// Import utilities
import { api } from './utils/api';

function App() {
  const [activeJobs, setActiveJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [globalStats, setGlobalStats] = useState(null);
  const [notificationAnchor, setNotificationAnchor] = useState(null);
  
  // WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useWebSocket('/ws');
  
  // Notification system
  const { notifications, addNotification, markAsRead, unreadCount } = useNotifications();
  
  useEffect(() => {
    // Initialize application
    loadInitialData();
  }, []);
  
  useEffect(() => {
    // Handle WebSocket messages
    if (lastMessage) {
      handleWebSocketMessage(lastMessage);
    }
  }, [lastMessage]);
  
  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Load global statistics
      const statsResponse = await api.get('/api/videos/stats');
      setGlobalStats(statsResponse.data);
      
      // Load active jobs
      const queueResponse = await api.get('/api/compress/queue');
      setActiveJobs(queueResponse.data.running_jobs || 0);
      
    } catch (error) {
      console.error('Failed to load initial data:', error);
      addNotification('Failed to load application data', 'error');
    } finally {
      setLoading(false);
    }
  };
  
  const handleWebSocketMessage = (message) => {
    if (message.type === 'progress_update') {
      const { data } = message;
      
      // Add progress notification for significant events
      if (data.event_type === 'completed') {
        addNotification(`Job ${data.job_id} completed successfully`, 'success');
      } else if (data.event_type === 'error') {
        addNotification(`Job ${data.job_id} failed: ${data.message}`, 'error');
      }
      
      // Update active jobs count
      loadQueueStatus();
    }
  };
  
  const loadQueueStatus = async () => {
    try {
      const response = await api.get('/api/compress/queue');
      setActiveJobs(response.data.running_jobs || 0);
    } catch (error) {
      console.error('Failed to load queue status:', error);
    }
  };
  
  const handleNotificationClick = (event) => {
    setNotificationAnchor(event.currentTarget);
  };
  
  const handleNotificationClose = () => {
    setNotificationAnchor(null);
  };
  
  const handleNotificationItemClick = (notification) => {
    markAsRead(notification.id);
    // Could add navigation logic here based on notification type
  };
  
  if (loading) {
    return (
      <Backdrop open={true} style={{ zIndex: 9999, color: '#fff' }}>
        <Box display="flex" flexDirection="column" alignItems="center">
          <CircularProgress color="inherit" size={60} />
          <Typography variant="h6" style={{ marginTop: 16 }}>
            Loading Mouse Video Compressor...
          </Typography>
        </Box>
      </Backdrop>
    );
  }
  
  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', backgroundColor: 'background.default' }}>
      {/* Application Header */}
      <AppBar position="sticky" elevation={1}>
        <Toolbar>
          <VideoLibraryIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Mouse Video Compressor
          </Typography>
          
          {/* Connection Status */}
          <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: isConnected ? '#4caf50' : '#f44336',
                mr: 1
              }}
            />
            <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </Typography>
          </Box>
          
          {/* Active Jobs Indicator */}
          {activeJobs > 0 && (
            <Tooltip title={`${activeJobs} active jobs`}>
              <Badge badgeContent={activeJobs} color="secondary">
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    px: 1,
                    py: 0.5,
                    backgroundColor: 'rgba(255,255,255,0.1)',
                    borderRadius: 1,
                    mr: 1
                  }}
                >
                  <CircularProgress size={16} sx={{ color: 'white', mr: 1 }} />
                  <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                    Processing
                  </Typography>
                </Box>
              </Badge>
            </Tooltip>
          )}
          
          {/* Notifications */}
          <Tooltip title="Notifications">
            <IconButton
              color="inherit"
              onClick={handleNotificationClick}
              sx={{ mr: 1 }}
            >
              <Badge badgeContent={unreadCount} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>
          
          {/* Settings */}
          <Tooltip title="Settings">
            <IconButton color="inherit">
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>
      
      {/* Notifications Menu */}
      <Menu
        anchorEl={notificationAnchor}
        open={Boolean(notificationAnchor)}
        onClose={handleNotificationClose}
        PaperProps={{
          sx: { width: 320, maxHeight: 400 }
        }}
      >
        {notifications.length === 0 ? (
          <MenuItem disabled>
            <Typography variant="body2" color="textSecondary">
              No notifications
            </Typography>
          </MenuItem>
        ) : (
          notifications.slice(0, 5).map((notification) => (
            <MenuItem
              key={notification.id}
              onClick={() => handleNotificationItemClick(notification)}
              sx={{
                backgroundColor: notification.read ? 'transparent' : 'rgba(25, 118, 210, 0.08)',
                borderLeft: notification.read ? 'none' : '3px solid #1976d2'
              }}
            >
              <Box>
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: notification.read ? 'normal' : 'bold',
                    mb: 0.5
                  }}
                >
                  {notification.message}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {new Date(notification.timestamp).toLocaleString()}
                </Typography>
              </Box>
            </MenuItem>
          ))
        )}
        {notifications.length > 5 && (
          <MenuItem>
            <Typography variant="body2" color="primary">
              View all notifications
            </Typography>
          </MenuItem>
        )}
      </Menu>
      
      {/* Main Content */}
      <Box sx={{ flexGrow: 1 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route 
            path="/dashboard" 
            element={
              <Dashboard 
                globalStats={globalStats}
                activeJobs={activeJobs}
                onRefresh={loadInitialData}
              />
            } 
          />
          <Route 
            path="/videos" 
            element={
              <VideoLibrary 
                onStatsUpdate={setGlobalStats}
              />
            } 
          />
          <Route 
            path="/queue" 
            element={
              <CompressionQueue 
                onJobsUpdate={setActiveJobs}
              />
            } 
          />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Box>
      
      {/* Footer */}
      <Box
        component="footer"
        sx={{
          py: 2,
          px: 3,
          backgroundColor: 'background.paper',
          borderTop: 1,
          borderColor: 'divider',
          mt: 'auto'
        }}
      >
        <Typography variant="body2" color="textSecondary" align="center">
          Mouse Video Compressor v1.0.0 - Adaptive compression for behavioral research
        </Typography>
      </Box>
    </Box>
  );
}

export default App;