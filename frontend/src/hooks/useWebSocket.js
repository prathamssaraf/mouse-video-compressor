import { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';

export const useWebSocket = (url = '/ws') => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [connectionError, setConnectionError] = useState(null);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000; // 3 seconds

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    try {
      // Create WebSocket connection
      const wsUrl = url.startsWith('ws') ? url : `ws://${window.location.host}${url}`;
      socketRef.current = new WebSocket(wsUrl);

      socketRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttempts.current = 0;
      };

      socketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
          setLastMessage({ type: 'raw', data: event.data });
        }
      };

      socketRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt to reconnect if it wasn't a manual close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          scheduleReconnect();
        }
      };

      socketRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionError('Connection failed');
        setIsConnected(false);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionError('Failed to create connection');
      scheduleReconnect();
    }
  }, [url]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttempts.current < maxReconnectAttempts) {
      reconnectAttempts.current += 1;
      console.log(`Attempting to reconnect... (${reconnectAttempts.current}/${maxReconnectAttempts})`);
      
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, reconnectDelay * reconnectAttempts.current);
    } else {
      setConnectionError('Max reconnection attempts reached');
    }
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (socketRef.current) {
      socketRef.current.close(1000, 'Manual disconnect');
      socketRef.current = null;
    }

    setIsConnected(false);
    setLastMessage(null);
    setConnectionError(null);
    reconnectAttempts.current = 0;
  }, []);

  const sendMessage = useCallback((message) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      const messageStr = typeof message === 'string' ? message : JSON.stringify(message);
      socketRef.current.send(messageStr);
      return true;
    } else {
      console.warn('WebSocket is not connected');
      return false;
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Auto-reconnect when the page becomes visible again
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !isConnected && !socketRef.current) {
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [connect, isConnected]);

  return {
    isConnected,
    lastMessage,
    connectionError,
    sendMessage,
    connect,
    disconnect,
    reconnectAttempts: reconnectAttempts.current,
    maxReconnectAttempts
  };
};