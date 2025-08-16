import { useState, useCallback, useRef, useEffect } from 'react';
import { api } from '../utils/api';

export const useVideoProcessing = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState({});
  const [analysisProgress, setAnalysisProgress] = useState({});
  const [compressionProgress, setCompressionProgress] = useState({});
  
  const abortControllers = useRef(new Map());

  // Load videos from API
  const loadVideos = useCallback(async (searchParams = {}) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.get('/api/videos', {
        params: searchParams
      });
      
      setVideos(response.data.videos || []);
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to load videos';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  // Upload video file
  const uploadVideo = useCallback(async (file, metadata = {}) => {
    const uploadId = `upload_${Date.now()}`;
    
    try {
      setUploadProgress(prev => ({
        ...prev,
        [uploadId]: { progress: 0, status: 'uploading', filename: file.name }
      }));

      const formData = new FormData();
      formData.append('file', file);
      formData.append('metadata', JSON.stringify(metadata));

      // Create abort controller for this upload
      const controller = new AbortController();
      abortControllers.current.set(uploadId, controller);

      const response = await api.post('/api/videos/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        signal: controller.signal,
        onUploadProgress: (progressEvent) => {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(prev => ({
            ...prev,
            [uploadId]: { 
              ...prev[uploadId], 
              progress,
              status: progress === 100 ? 'processing' : 'uploading'
            }
          }));
        }
      });

      setUploadProgress(prev => ({
        ...prev,
        [uploadId]: { 
          ...prev[uploadId], 
          progress: 100, 
          status: 'completed',
          videoId: response.data.video_id
        }
      }));

      // Refresh video list
      await loadVideos();
      
      return response.data;
    } catch (err) {
      if (err.name === 'AbortError') {
        setUploadProgress(prev => ({
          ...prev,
          [uploadId]: { ...prev[uploadId], status: 'cancelled' }
        }));
      } else {
        setUploadProgress(prev => ({
          ...prev,
          [uploadId]: { 
            ...prev[uploadId], 
            status: 'error', 
            error: err.response?.data?.detail || err.message 
          }
        }));
      }
      throw err;
    } finally {
      abortControllers.current.delete(uploadId);
    }
  }, [loadVideos]);

  // Cancel upload
  const cancelUpload = useCallback((uploadId) => {
    const controller = abortControllers.current.get(uploadId);
    if (controller) {
      controller.abort();
      setUploadProgress(prev => ({
        ...prev,
        [uploadId]: { ...prev[uploadId], status: 'cancelled' }
      }));
    }
  }, []);

  // Start video analysis
  const analyzeVideo = useCallback(async (videoId, options = {}) => {
    try {
      setAnalysisProgress(prev => ({
        ...prev,
        [videoId]: { progress: 0, status: 'starting', stage: 'initializing' }
      }));

      const response = await api.post(`/api/videos/${videoId}/analyze`, options);
      
      setAnalysisProgress(prev => ({
        ...prev,
        [videoId]: { progress: 0, status: 'running', stage: 'motion_analysis' }
      }));

      return response.data;
    } catch (err) {
      setAnalysisProgress(prev => ({
        ...prev,
        [videoId]: { 
          status: 'error', 
          error: err.response?.data?.detail || err.message 
        }
      }));
      throw err;
    }
  }, []);

  // Start video compression
  const compressVideo = useCallback(async (videoId, settings) => {
    try {
      setCompressionProgress(prev => ({
        ...prev,
        [videoId]: { progress: 0, status: 'starting', stage: 'initializing' }
      }));

      const response = await api.post('/api/compress/start', {
        input_video_id: videoId,
        settings: settings
      });

      const jobId = response.data.job_id;
      
      setCompressionProgress(prev => ({
        ...prev,
        [videoId]: { 
          progress: 0, 
          status: 'running', 
          stage: 'compression',
          jobId: jobId 
        }
      }));

      return response.data;
    } catch (err) {
      setCompressionProgress(prev => ({
        ...prev,
        [videoId]: { 
          status: 'error', 
          error: err.response?.data?.detail || err.message 
        }
      }));
      throw err;
    }
  }, []);

  // Batch compress videos
  const batchCompress = useCallback(async (videoIds, settings) => {
    try {
      const response = await api.post('/api/compress/batch', {
        video_ids: videoIds,
        settings: settings
      });

      // Initialize progress for all videos
      videoIds.forEach(videoId => {
        setCompressionProgress(prev => ({
          ...prev,
          [videoId]: { progress: 0, status: 'queued', stage: 'waiting' }
        }));
      });

      return response.data;
    } catch (err) {
      // Mark all videos as failed
      videoIds.forEach(videoId => {
        setCompressionProgress(prev => ({
          ...prev,
          [videoId]: { 
            status: 'error', 
            error: err.response?.data?.detail || err.message 
          }
        }));
      });
      throw err;
    }
  }, []);

  // Update video metadata
  const updateVideo = useCallback(async (videoId, updateData) => {
    try {
      const response = await api.put(`/api/videos/${videoId}`, updateData);
      
      // Update local state
      setVideos(prev => prev.map(video => 
        video.id === videoId 
          ? { ...video, ...updateData }
          : video
      ));

      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || err.message);
    }
  }, []);

  // Delete video
  const deleteVideo = useCallback(async (videoId) => {
    try {
      await api.delete(`/api/videos/${videoId}`);
      
      // Remove from local state
      setVideos(prev => prev.filter(video => video.id !== videoId));
      
      // Clean up progress states
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        Object.keys(newProgress).forEach(key => {
          if (newProgress[key].videoId === videoId) {
            delete newProgress[key];
          }
        });
        return newProgress;
      });
      
      setAnalysisProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[videoId];
        return newProgress;
      });
      
      setCompressionProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[videoId];
        return newProgress;
      });

    } catch (err) {
      throw new Error(err.response?.data?.detail || err.message);
    }
  }, []);

  // Get video by ID
  const getVideo = useCallback(async (videoId) => {
    try {
      const response = await api.get(`/api/videos/${videoId}`);
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || err.message);
    }
  }, []);

  // Get video preview
  const getVideoPreview = useCallback(async (videoId, timestamp = 0) => {
    try {
      const response = await api.get(`/api/videos/${videoId}/preview`, {
        params: { timestamp },
        responseType: 'blob'
      });
      
      // Create object URL for the image blob
      const imageUrl = URL.createObjectURL(response.data);
      return imageUrl;
    } catch (err) {
      throw new Error(err.response?.data?.detail || err.message);
    }
  }, []);

  // Update progress from WebSocket messages
  const updateProgressFromMessage = useCallback((message) => {
    if (message.type === 'progress_update') {
      const { data } = message;
      const { job_id, percentage, stage, event_type } = data;
      
      // Find video by job ID (this is simplified - in real app you'd track job-to-video mapping)
      const videoId = Object.keys(compressionProgress).find(id => 
        compressionProgress[id].jobId === job_id
      );
      
      if (videoId) {
        setCompressionProgress(prev => ({
          ...prev,
          [videoId]: {
            ...prev[videoId],
            progress: percentage,
            stage: stage,
            status: event_type === 'completed' ? 'completed' :
                   event_type === 'error' ? 'error' :
                   event_type === 'cancelled' ? 'cancelled' : 'running'
          }
        }));
      }
    }
  }, [compressionProgress]);

  // Clean up progress entries
  const clearProgress = useCallback((type, id) => {
    switch (type) {
      case 'upload':
        setUploadProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[id];
          return newProgress;
        });
        break;
      case 'analysis':
        setAnalysisProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[id];
          return newProgress;
        });
        break;
      case 'compression':
        setCompressionProgress(prev => {
          const newProgress = { ...prev };
          delete newProgress[id];
          return newProgress;
        });
        break;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cancel all pending uploads
      abortControllers.current.forEach(controller => {
        controller.abort();
      });
      abortControllers.current.clear();
    };
  }, []);

  return {
    // Data
    videos,
    loading,
    error,
    uploadProgress,
    analysisProgress,
    compressionProgress,
    
    // Actions
    loadVideos,
    uploadVideo,
    cancelUpload,
    analyzeVideo,
    compressVideo,
    batchCompress,
    updateVideo,
    deleteVideo,
    getVideo,
    getVideoPreview,
    updateProgressFromMessage,
    clearProgress
  };
};