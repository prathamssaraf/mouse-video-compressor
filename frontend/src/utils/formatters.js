// File size formatting
export const formatFileSize = (bytes, decimals = 2) => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};

// Duration formatting
export const formatDuration = (seconds, showHours = true) => {
  if (!seconds || seconds < 0) return '00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (showHours && hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  } else {
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
};

// Duration in human readable format
export const formatDurationHuman = (seconds) => {
  if (!seconds || seconds < 0) return '0 seconds';
  
  const units = [
    { label: 'day', value: 24 * 60 * 60 },
    { label: 'hour', value: 60 * 60 },
    { label: 'minute', value: 60 },
    { label: 'second', value: 1 }
  ];
  
  const parts = [];
  let remaining = Math.floor(seconds);
  
  for (const unit of units) {
    if (remaining >= unit.value) {
      const count = Math.floor(remaining / unit.value);
      parts.push(`${count} ${unit.label}${count !== 1 ? 's' : ''}`);
      remaining %= unit.value;
    }
    
    // Stop after 2 units for readability
    if (parts.length >= 2) break;
  }
  
  return parts.join(', ') || '0 seconds';
};

// Date formatting
export const formatDate = (date, options = {}) => {
  if (!date) return 'Unknown';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  
  const defaultOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options
  };
  
  return dateObj.toLocaleDateString('en-US', defaultOptions);
};

// Relative time formatting (e.g., "2 hours ago")
export const formatRelativeTime = (date) => {
  if (!date) return 'Unknown';
  
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffInSeconds = Math.floor((now - dateObj) / 1000);
  
  if (diffInSeconds < 60) {
    return 'Just now';
  }
  
  const intervals = [
    { label: 'year', seconds: 31536000 },
    { label: 'month', seconds: 2592000 },
    { label: 'week', seconds: 604800 },
    { label: 'day', seconds: 86400 },
    { label: 'hour', seconds: 3600 },
    { label: 'minute', seconds: 60 }
  ];
  
  for (const interval of intervals) {
    const count = Math.floor(diffInSeconds / interval.seconds);
    if (count >= 1) {
      return `${count} ${interval.label}${count !== 1 ? 's' : ''} ago`;
    }
  }
  
  return 'Just now';
};

// Percentage formatting
export const formatPercentage = (value, decimals = 1) => {
  if (value === null || value === undefined) return 'N/A';
  return `${(value * 100).toFixed(decimals)}%`;
};

// Number formatting with commas
export const formatNumber = (num, decimals = 0) => {
  if (num === null || num === undefined) return 'N/A';
  return num.toLocaleString('en-US', { 
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals 
  });
};

// Compression ratio formatting
export const formatCompressionRatio = (ratio) => {
  if (!ratio || ratio <= 0) return 'N/A';
  
  const percentage = (1 - ratio) * 100;
  return `${percentage.toFixed(1)}% reduction`;
};

// Activity level formatting
export const formatActivityLevel = (ratio) => {
  if (ratio === null || ratio === undefined) return 'Unknown';
  
  if (ratio > 0.8) return 'Very High';
  if (ratio > 0.6) return 'High';
  if (ratio > 0.4) return 'Moderate';
  if (ratio > 0.2) return 'Low';
  return 'Very Low';
};

// Video resolution formatting
export const formatResolution = (width, height) => {
  if (!width || !height) return 'Unknown';
  
  // Common resolution names
  const resolutions = {
    '1920x1080': '1080p (Full HD)',
    '1280x720': '720p (HD)',
    '640x480': '480p (SD)',
    '3840x2160': '4K (Ultra HD)',
    '2560x1440': '1440p (QHD)',
    '1366x768': '768p',
    '1024x768': '768p (4:3)',
    '800x600': '600p (4:3)'
  };
  
  const key = `${width}x${height}`;
  return resolutions[key] || `${width}x${height}`;
};

// Processing speed formatting
export const formatProcessingSpeed = (fps) => {
  if (!fps || fps <= 0) return 'N/A';
  
  if (fps >= 1) {
    return `${fps.toFixed(1)}x realtime`;
  } else {
    return `${(fps * 100).toFixed(0)}% realtime`;
  }
};

// Bit rate formatting
export const formatBitrate = (bitsPerSecond) => {
  if (!bitsPerSecond || bitsPerSecond <= 0) return 'N/A';
  
  const units = ['bps', 'Kbps', 'Mbps', 'Gbps'];
  let value = bitsPerSecond;
  let unitIndex = 0;
  
  while (value >= 1000 && unitIndex < units.length - 1) {
    value /= 1000;
    unitIndex++;
  }
  
  return `${value.toFixed(1)} ${units[unitIndex]}`;
};

// Status color mapping
export const getStatusColor = (status) => {
  const colorMap = {
    // Job statuses
    pending: 'warning',
    queued: 'info',
    running: 'primary',
    completed: 'success',
    failed: 'error',
    cancelled: 'default',
    paused: 'warning',
    
    // Video statuses
    available: 'success',
    processing: 'primary',
    error: 'error',
    deleted: 'default',
    
    // Activity levels
    'very high': 'error',
    'high': 'warning',
    'moderate': 'info',
    'low': 'success',
    'very low': 'success'
  };
  
  return colorMap[status?.toLowerCase()] || 'default';
};

// Status icon mapping
export const getStatusIcon = (status) => {
  const iconMap = {
    // Job statuses
    pending: 'schedule',
    queued: 'queue',
    running: 'play_circle',
    completed: 'check_circle',
    failed: 'error',
    cancelled: 'cancel',
    paused: 'pause_circle',
    
    // Video statuses
    available: 'video_library',
    processing: 'movie_filter',
    error: 'error_outline',
    
    // Activity levels
    'very high': 'trending_up',
    'high': 'trending_up',
    'moderate': 'trending_flat',
    'low': 'trending_down',
    'very low': 'trending_down'
  };
  
  return iconMap[status?.toLowerCase()] || 'help_outline';
};

// Priority formatting
export const formatPriority = (priority) => {
  const priorityMap = {
    low: 'Low',
    normal: 'Normal',
    high: 'High',
    urgent: 'Urgent'
  };
  
  return priorityMap[priority?.toLowerCase()] || 'Normal';
};

// Estimated time formatting
export const formatEstimatedTime = (seconds) => {
  if (!seconds || seconds <= 0) return 'Unknown';
  
  if (seconds < 60) {
    return `${Math.ceil(seconds)} seconds`;
  } else if (seconds < 3600) {
    const minutes = Math.ceil(seconds / 60);
    return `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const remainingMinutes = Math.ceil((seconds % 3600) / 60);
    
    if (remainingMinutes === 0) {
      return `${hours} hour${hours !== 1 ? 's' : ''}`;
    } else {
      return `${hours}h ${remainingMinutes}m`;
    }
  }
};

// Video format formatting
export const formatVideoFormat = (format) => {
  const formatMap = {
    mp4: 'MP4',
    avi: 'AVI',
    mov: 'MOV',
    wmv: 'WMV',
    mkv: 'MKV',
    webm: 'WebM',
    flv: 'FLV'
  };
  
  return formatMap[format?.toLowerCase()] || format?.toUpperCase() || 'Unknown';
};

// Error message formatting
export const formatErrorMessage = (error) => {
  if (typeof error === 'string') {
    return error;
  }
  
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }
  
  if (error?.message) {
    return error.message;
  }
  
  return 'An unknown error occurred';
};

// Progress message formatting
export const formatProgressMessage = (stage, percentage) => {
  const stageMessages = {
    initializing: 'Initializing...',
    motion_analysis: `Analyzing motion patterns... ${percentage.toFixed(1)}%`,
    segment_compression: `Compressing video segments... ${percentage.toFixed(1)}%`,
    concatenation: 'Combining compressed segments...',
    finalizing: 'Finalizing compression...',
    cleanup: 'Cleaning up temporary files...',
    completed: 'Compression completed successfully',
    error: 'An error occurred during processing',
    cancelled: 'Processing was cancelled'
  };
  
  return stageMessages[stage] || `Processing... ${percentage.toFixed(1)}%`;
};

// Tags formatting for display
export const formatTags = (tags) => {
  if (!tags || !Array.isArray(tags) || tags.length === 0) {
    return 'No tags';
  }
  
  if (tags.length <= 3) {
    return tags.join(', ');
  } else {
    return `${tags.slice(0, 3).join(', ')} +${tags.length - 3} more`;
  }
};

// Search query highlighting
export const highlightSearchText = (text, searchQuery) => {
  if (!searchQuery || !text) return text;
  
  const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
};

// Utility to format any value based on its type
export const formatValue = (value, type, options = {}) => {
  switch (type) {
    case 'fileSize':
      return formatFileSize(value, options.decimals);
    case 'duration':
      return formatDuration(value, options.showHours);
    case 'durationHuman':
      return formatDurationHuman(value);
    case 'date':
      return formatDate(value, options);
    case 'relativeTime':
      return formatRelativeTime(value);
    case 'percentage':
      return formatPercentage(value, options.decimals);
    case 'number':
      return formatNumber(value, options.decimals);
    case 'compressionRatio':
      return formatCompressionRatio(value);
    case 'activityLevel':
      return formatActivityLevel(value);
    case 'resolution':
      return formatResolution(value.width, value.height);
    case 'processingSpeed':
      return formatProcessingSpeed(value);
    case 'bitrate':
      return formatBitrate(value);
    case 'estimatedTime':
      return formatEstimatedTime(value);
    case 'videoFormat':
      return formatVideoFormat(value);
    case 'priority':
      return formatPriority(value);
    case 'tags':
      return formatTags(value);
    default:
      return value?.toString() || 'N/A';
  }
};