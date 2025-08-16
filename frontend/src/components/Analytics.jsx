import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Paper,
  Alert
} from '@mui/material';
import { Line, Bar, Doughnut } from 'react-chartjs-2';

const Analytics = () => {
  const [analyticsData, setAnalyticsData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load analytics data
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      // Mock data for demonstration
      setAnalyticsData({
        compressionStats: {
          totalSpaceSaved: 1250, // GB
          averageCompressionRatio: 0.65,
          totalJobsCompleted: 342
        }
      });
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  // Mock chart data
  const compressionTrendData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [
      {
        label: 'Space Saved (GB)',
        data: [120, 190, 300, 500, 200, 300],
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
      }
    ]
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="400px">
        <Typography>Loading analytics...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Analytics
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Analytics dashboard coming soon. This will show compression statistics, 
        motion analysis insights, and system performance metrics.
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compression Trends
              </Typography>
              <Box height={300}>
                <Line
                  data={compressionTrendData}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false
                  }}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Summary Statistics
              </Typography>
              {analyticsData && (
                <Box>
                  <Typography variant="body1" gutterBottom>
                    Total Space Saved: {analyticsData.compressionStats.totalSpaceSaved} GB
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    Average Compression: {(analyticsData.compressionStats.averageCompressionRatio * 100).toFixed(1)}%
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    Jobs Completed: {analyticsData.compressionStats.totalJobsCompleted}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Analytics;