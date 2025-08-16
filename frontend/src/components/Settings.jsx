import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Alert,
  Divider,
  Slider,
  MenuItem
} from '@mui/material';

const Settings = () => {
  const [settings, setSettings] = useState({
    compression: {
      defaultProfile: 'balanced',
      enableROI: true,
      maxConcurrentJobs: 2
    },
    motionDetection: {
      threshold: 0.02,
      backgroundLearningRate: 0.001,
      minInactiveDuration: 30
    },
    system: {
      autoAnalyze: true,
      maxFileSize: 10, // GB
      retentionDays: 30
    }
  });
  
  const [loading, setLoading] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const handleSettingChange = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      // Save settings to backend
      console.log('Saving settings:', settings);
      setSaveMessage('Settings saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (error) {
      setSaveMessage('Failed to save settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      {saveMessage && (
        <Alert 
          severity={saveMessage.includes('success') ? 'success' : 'error'} 
          sx={{ mb: 3 }}
        >
          {saveMessage}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Compression Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compression Settings
              </Typography>
              
              <TextField
                fullWidth
                select
                label="Default Profile"
                value={settings.compression.defaultProfile}
                onChange={(e) => handleSettingChange('compression', 'defaultProfile', e.target.value)}
                sx={{ mb: 2 }}
              >
                <MenuItem value="conservative">Conservative</MenuItem>
                <MenuItem value="balanced">Balanced</MenuItem>
                <MenuItem value="aggressive">Aggressive</MenuItem>
              </TextField>

              <FormControlLabel
                control={
                  <Switch
                    checked={settings.compression.enableROI}
                    onChange={(e) => handleSettingChange('compression', 'enableROI', e.target.checked)}
                  />
                }
                label="Enable ROI-based compression"
                sx={{ mb: 2 }}
              />

              <Typography gutterBottom>
                Max Concurrent Jobs: {settings.compression.maxConcurrentJobs}
              </Typography>
              <Slider
                value={settings.compression.maxConcurrentJobs}
                onChange={(e, value) => handleSettingChange('compression', 'maxConcurrentJobs', value)}
                min={1}
                max={8}
                marks
                sx={{ mb: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Motion Detection Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Motion Detection Settings
              </Typography>
              
              <Typography gutterBottom>
                Motion Threshold: {settings.motionDetection.threshold}
              </Typography>
              <Slider
                value={settings.motionDetection.threshold}
                onChange={(e, value) => handleSettingChange('motionDetection', 'threshold', value)}
                min={0.001}
                max={0.1}
                step={0.001}
                sx={{ mb: 2 }}
              />

              <Typography gutterBottom>
                Background Learning Rate: {settings.motionDetection.backgroundLearningRate}
              </Typography>
              <Slider
                value={settings.motionDetection.backgroundLearningRate}
                onChange={(e, value) => handleSettingChange('motionDetection', 'backgroundLearningRate', value)}
                min={0.0001}
                max={0.01}
                step={0.0001}
                sx={{ mb: 2 }}
              />

              <TextField
                fullWidth
                type="number"
                label="Min Inactive Duration (seconds)"
                value={settings.motionDetection.minInactiveDuration}
                onChange={(e) => handleSettingChange('motionDetection', 'minInactiveDuration', parseInt(e.target.value))}
                sx={{ mb: 2 }}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* System Settings */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                System Settings
              </Typography>
              
              <FormControlLabel
                control={
                  <Switch
                    checked={settings.system.autoAnalyze}
                    onChange={(e) => handleSettingChange('system', 'autoAnalyze', e.target.checked)}
                  />
                }
                label="Automatically analyze uploaded videos"
                sx={{ mb: 2 }}
              />

              <TextField
                type="number"
                label="Max File Size (GB)"
                value={settings.system.maxFileSize}
                onChange={(e) => handleSettingChange('system', 'maxFileSize', parseInt(e.target.value))}
                sx={{ mb: 2, mr: 2, width: 200 }}
              />

              <TextField
                type="number"
                label="Log Retention (days)"
                value={settings.system.retentionDays}
                onChange={(e) => handleSettingChange('system', 'retentionDays', parseInt(e.target.value))}
                sx={{ mb: 2, width: 200 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save Settings'}
        </Button>
      </Box>
    </Box>
  );
};

export default Settings;