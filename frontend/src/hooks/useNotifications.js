import { useState, useCallback, useEffect } from 'react';

const STORAGE_KEY = 'video_compressor_notifications';
const MAX_NOTIFICATIONS = 100;

export const useNotifications = () => {
  const [notifications, setNotifications] = useState([]);

  // Load notifications from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        setNotifications(parsed);
      }
    } catch (error) {
      console.error('Failed to load notifications from storage:', error);
    }
  }, []);

  // Save notifications to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
    } catch (error) {
      console.error('Failed to save notifications to storage:', error);
    }
  }, [notifications]);

  // Add a new notification
  const addNotification = useCallback((message, type = 'info', options = {}) => {
    const notification = {
      id: `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      message,
      type, // 'success', 'error', 'warning', 'info'
      timestamp: new Date().toISOString(),
      read: false,
      persistent: options.persistent || false,
      data: options.data || null,
      actionLabel: options.actionLabel || null,
      actionCallback: options.actionCallback || null
    };

    setNotifications(prev => {
      const newNotifications = [notification, ...prev];
      
      // Keep only the most recent notifications
      if (newNotifications.length > MAX_NOTIFICATIONS) {
        return newNotifications.slice(0, MAX_NOTIFICATIONS);
      }
      
      return newNotifications;
    });

    // Auto-dismiss non-persistent notifications after a delay
    if (!notification.persistent) {
      const dismissDelay = type === 'error' ? 8000 : 5000;
      setTimeout(() => {
        removeNotification(notification.id);
      }, dismissDelay);
    }

    return notification.id;
  }, []);

  // Remove a notification
  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(notification => notification.id !== id));
  }, []);

  // Mark notification as read
  const markAsRead = useCallback((id) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === id 
          ? { ...notification, read: true }
          : notification
      )
    );
  }, []);

  // Mark all notifications as read
  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(notification => ({ ...notification, read: true }))
    );
  }, []);

  // Clear all notifications
  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  // Clear only read notifications
  const clearRead = useCallback(() => {
    setNotifications(prev => prev.filter(notification => !notification.read));
  }, []);

  // Get notifications by type
  const getByType = useCallback((type) => {
    return notifications.filter(notification => notification.type === type);
  }, [notifications]);

  // Get recent notifications (last N)
  const getRecent = useCallback((count = 10) => {
    return notifications.slice(0, count);
  }, [notifications]);

  // Computed values
  const unreadCount = notifications.filter(n => !n.read).length;
  const hasUnread = unreadCount > 0;
  const latestNotification = notifications[0] || null;

  // Predefined notification creators for common scenarios
  const notifySuccess = useCallback((message, options = {}) => {
    return addNotification(message, 'success', options);
  }, [addNotification]);

  const notifyError = useCallback((message, options = {}) => {
    return addNotification(message, 'error', { persistent: true, ...options });
  }, [addNotification]);

  const notifyWarning = useCallback((message, options = {}) => {
    return addNotification(message, 'warning', options);
  }, [addNotification]);

  const notifyInfo = useCallback((message, options = {}) => {
    return addNotification(message, 'info', options);
  }, [addNotification]);

  // Specialized notifications for video processing
  const notifyVideoUploaded = useCallback((filename, videoId) => {
    return addNotification(
      `Video "${filename}" uploaded successfully`,
      'success',
      {
        data: { videoId, filename },
        actionLabel: 'View',
        actionCallback: () => {
          // Could navigate to video details
          console.log('Navigate to video:', videoId);
        }
      }
    );
  }, [addNotification]);

  const notifyVideoAnalysisComplete = useCallback((filename, videoId) => {
    return addNotification(
      `Motion analysis completed for "${filename}"`,
      'success',
      {
        data: { videoId, filename },
        actionLabel: 'View Results',
        actionCallback: () => {
          // Could navigate to analysis results
          console.log('View analysis for video:', videoId);
        }
      }
    );
  }, [addNotification]);

  const notifyCompressionComplete = useCallback((filename, savings) => {
    return addNotification(
      `Compression completed for "${filename}". Space saved: ${savings}`,
      'success',
      {
        data: { filename, savings },
        actionLabel: 'Download',
        actionCallback: () => {
          // Could trigger download
          console.log('Download compressed video:', filename);
        }
      }
    );
  }, [addNotification]);

  const notifyJobFailed = useCallback((jobType, filename, error) => {
    return addNotification(
      `${jobType} failed for "${filename}": ${error}`,
      'error',
      {
        persistent: true,
        data: { jobType, filename, error },
        actionLabel: 'Retry',
        actionCallback: () => {
          // Could trigger retry logic
          console.log('Retry job for:', filename);
        }
      }
    );
  }, [addNotification]);

  const notifySystemAlert = useCallback((message, severity = 'warning') => {
    return addNotification(
      message,
      severity,
      {
        persistent: severity === 'error',
        data: { type: 'system_alert' }
      }
    );
  }, [addNotification]);

  return {
    // State
    notifications,
    unreadCount,
    hasUnread,
    latestNotification,
    
    // Basic actions
    addNotification,
    removeNotification,
    markAsRead,
    markAllAsRead,
    clearAll,
    clearRead,
    
    // Query functions
    getByType,
    getRecent,
    
    // Convenience creators
    notifySuccess,
    notifyError,
    notifyWarning,
    notifyInfo,
    
    // Specialized creators
    notifyVideoUploaded,
    notifyVideoAnalysisComplete,
    notifyCompressionComplete,
    notifyJobFailed,
    notifySystemAlert
  };
};