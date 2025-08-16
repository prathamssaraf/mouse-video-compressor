import axios from 'axios';

// Create axios instance with default configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '',
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth tokens, request ID, etc.
api.interceptors.request.use(
  (config) => {
    // Add request timestamp
    config.metadata = { startTime: new Date() };
    
    // Add request ID for tracking
    config.headers['X-Request-ID'] = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // Add auth token if available
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling common errors and logging
api.interceptors.response.use(
  (response) => {
    // Calculate request duration
    const duration = new Date() - response.config.metadata.startTime;
    
    // Log successful requests in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`✅ ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`);
    }
    
    return response;
  },
  (error) => {
    // Calculate request duration
    const duration = error.config?.metadata?.startTime 
      ? new Date() - error.config.metadata.startTime 
      : 0;
    
    // Log failed requests
    console.error(`❌ ${error.config?.method?.toUpperCase()} ${error.config?.url} - ${duration}ms`, error);
    
    // Handle specific error cases
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          // Unauthorized - redirect to login or refresh token
          handleUnauthorized();
          break;
        case 403:
          // Forbidden
          console.warn('Access forbidden:', data?.detail || 'Insufficient permissions');
          break;
        case 404:
          // Not found
          console.warn('Resource not found:', error.config?.url);
          break;
        case 429:
          // Rate limited
          console.warn('Rate limited. Please slow down your requests.');
          break;
        case 500:
          // Server error
          console.error('Server error:', data?.detail || 'Internal server error');
          break;
        default:
          console.error('HTTP error:', status, data?.detail || error.message);
      }
    } else if (error.request) {
      // Network error or no response
      console.error('Network error:', error.message);
      
      // Check if it's a timeout
      if (error.code === 'ECONNABORTED') {
        console.error('Request timeout');
      }
    } else {
      // Request configuration error
      console.error('Request error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// Helper function to handle unauthorized access
const handleUnauthorized = () => {
  // Clear stored token
  localStorage.removeItem('auth_token');
  
  // Could redirect to login page
  // window.location.href = '/login';
  
  console.warn('Authentication required');
};

// API methods organized by feature

const videoAPI = {
  // Get all videos with optional search parameters
  getAll: (params = {}) => api.get('/api/videos', { params }),
  
  // Get single video by ID
  getById: (id) => api.get(`/api/videos/${id}`),
  
  // Upload new video
  upload: (formData, onProgress) => api.post('/api/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress
  }),
  
  // Update video metadata
  update: (id, data) => api.put(`/api/videos/${id}`, data),
  
  // Delete video
  delete: (id) => api.delete(`/api/videos/${id}`),
  
  // Start video analysis
  analyze: (id, options = {}) => api.post(`/api/videos/${id}/analyze`, options),
  
  // Get video preview/thumbnail
  getPreview: (id, timestamp = 0) => api.get(`/api/videos/${id}/preview`, {
    params: { timestamp },
    responseType: 'blob'
  }),
  
  // Get video statistics
  getStats: () => api.get('/api/videos/stats'),
  
  // Batch operations
  batchOperation: (data) => api.post('/api/videos/batch', data)
};

const compressionAPI = {
  // Start compression job
  start: (data) => api.post('/api/compress/start', data),
  
  // Get job status
  getStatus: (jobId) => api.get(`/api/compress/${jobId}/status`),
  
  // Cancel job
  cancel: (jobId) => api.delete(`/api/compress/${jobId}`),
  
  // Get queue status
  getQueue: () => api.get('/api/compress/queue'),
  
  // Start batch compression
  batch: (data) => api.post('/api/compress/batch', data),
  
  // Get job list
  getJobs: (params = {}) => api.get('/api/compress/jobs', { params }),
  
  // Get compression statistics
  getStats: () => api.get('/api/compress/stats')
};

const settingsAPI = {
  // Get compression profiles
  getProfiles: () => api.get('/api/settings/profiles'),
  
  // Get profile recommendations for a video
  getRecommendations: (videoId) => api.get(`/api/settings/profiles/${videoId}/recommendations`),
  
  // Create custom profile
  createProfile: (data) => api.post('/api/settings/profiles', data),
  
  // Update motion detection settings
  updateMotionSettings: (data) => api.put('/api/settings/motion-detection', data),
  
  // Get system settings
  getSystemSettings: () => api.get('/api/settings/system'),
  
  // Update system settings
  updateSystemSettings: (data) => api.put('/api/settings/system', data)
};

const analyticsAPI = {
  // Get compression analytics
  getCompressionAnalytics: (params = {}) => api.get('/api/analytics/compression', { params }),
  
  // Get motion analysis analytics
  getMotionAnalytics: (params = {}) => api.get('/api/analytics/motion', { params }),
  
  // Get system performance metrics
  getPerformanceMetrics: (params = {}) => api.get('/api/analytics/performance', { params }),
  
  // Export analytics data
  exportData: (format = 'json', params = {}) => api.get('/api/analytics/export', {
    params: { format, ...params },
    responseType: format === 'csv' ? 'blob' : 'json'
  })
};

// Utility functions for common API patterns

const withRetry = async (apiCall, maxRetries = 3, delay = 1000) => {
  let lastError;
  
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await apiCall();
    } catch (error) {
      lastError = error;
      
      // Don't retry on client errors (4xx) except 429 (rate limit)
      if (error.response?.status >= 400 && error.response?.status < 500 && error.response?.status !== 429) {
        throw error;
      }
      
      if (attempt < maxRetries) {
        console.log(`API call failed, retrying in ${delay}ms (attempt ${attempt}/${maxRetries})`);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= 2; // Exponential backoff
      }
    }
  }
  
  throw lastError;
};

const withCache = (apiCall, cacheKey, ttlMs = 300000) => { // 5 minutes default TTL
  const cache = new Map();
  
  return async (...args) => {
    const key = `${cacheKey}_${JSON.stringify(args)}`;
    const cached = cache.get(key);
    
    if (cached && Date.now() - cached.timestamp < ttlMs) {
      return cached.data;
    }
    
    try {
      const data = await apiCall(...args);
      cache.set(key, { data, timestamp: Date.now() });
      return data;
    } catch (error) {
      // Return cached data if available, even if expired, in case of error
      if (cached) {
        console.warn('API call failed, returning cached data:', error.message);
        return cached.data;
      }
      throw error;
    }
  };
};

// Create cached versions of frequently accessed endpoints
const cachedVideoStats = withCache(videoAPI.getStats, 'video_stats', 60000); // 1 minute cache
const cachedProfiles = withCache(settingsAPI.getProfiles, 'profiles', 600000); // 10 minute cache

// Helper for building query strings
const buildQueryString = (params) => {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(item => searchParams.append(key, item));
      } else {
        searchParams.append(key, value);
      }
    }
  });
  
  return searchParams.toString();
};

// Helper for file downloads
const downloadFile = async (url, filename) => {
  try {
    const response = await api.get(url, { responseType: 'blob' });
    
    // Create blob URL
    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    
    // Create temporary link and trigger download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
    
    return true;
  } catch (error) {
    console.error('Download failed:', error);
    return false;
  }
};

// Helper for uploading files with progress
const uploadWithProgress = async (endpoint, file, metadata = {}, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  
  if (metadata && Object.keys(metadata).length > 0) {
    formData.append('metadata', JSON.stringify(metadata));
  }
  
  return api.post(endpoint, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress, progressEvent);
      }
    }
  });
};

// Export everything
export {
  api,
  videoAPI,
  compressionAPI,
  settingsAPI,
  analyticsAPI,
  withRetry,
  withCache,
  cachedVideoStats,
  cachedProfiles,
  buildQueryString,
  downloadFile,
  uploadWithProgress
};

// Default export
export default api;