import React, { useState, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  FormControlLabel,
  Switch,
  Alert,
  Button,
  Stack,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  CleaningServices as CleaningServicesIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useSettings } from '../SettingsContext';
import axios from 'axios';

/**
 * Settings page for configuring application options.
 */
const Settings: React.FC = () => {
  const { settings, refreshSettings } = useSettings();
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [cleaningUp, setCleaningUp] = useState(false);

  /**
   * Handle auto-cleanup toggle change.
   */
  const handleAutoCleanupChange = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const enabled = event.target.checked;
    setUpdating(true);
    setError(null);
    setSuccess(null);

    try {
      await axios.post('/api/config/auto_cleanup_enabled', {
        value: enabled
      });

      // Refresh settings to get updated value
      await refreshSettings();

      setSuccess(`Auto-cleanup ${enabled ? 'enabled' : 'disabled'} successfully`);
    } catch (err) {
      console.error('Failed to update auto-cleanup setting:', err);
      setError('Failed to update auto-cleanup setting. Please try again.');
    } finally {
      setUpdating(false);
    }
  }, [refreshSettings]);

  /**
   * Handle manual cleanup trigger.
   */
  const handleManualCleanup = useCallback(async () => {
    setCleaningUp(true);
    setError(null);
    setSuccess(null);

    try {
      await axios.post('/api/tv/files/cleanup');
      setSuccess('Manual cleanup completed successfully');
    } catch (err) {
      console.error('Failed to run manual cleanup:', err);
      const errorMessage = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        || 'Failed to run manual cleanup. Please try again.';
      setError(errorMessage);
    } finally {
      setCleaningUp(false);
    }
  }, []);

  if (!settings) {
    return (
      <Container maxWidth="md">
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        {/* Page Header */}
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
          <SettingsIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            Settings
          </Typography>
        </Stack>

        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Configure application settings and TV management options.
        </Typography>

        {/* Status Messages */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
            {success}
          </Alert>
        )}

        {/* TV Auto-cleanup Settings */}
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <CleaningServicesIcon sx={{ fontSize: 24, color: 'primary.main' }} />
            <Typography variant="h6" component="h2">
              TV Auto-cleanup
            </Typography>
          </Stack>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Automatically clean up old files on the Samsung Frame TV to prevent memory buildup.
            When enabled, the system will keep only the 3 most recent files and delete older ones every hour.
          </Typography>

          <FormControlLabel
            control={
              <Switch
                checked={settings.auto_cleanup_enabled}
                onChange={handleAutoCleanupChange}
                disabled={updating}
              />
            }
            label={
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography>
                  Enable automatic cleanup
                </Typography>
                {updating && <CircularProgress size={16} />}
              </Stack>
            }
          />

          <Box sx={{ mt: 2, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <InfoIcon fontSize="small" color="info" sx={{ mt: 0.5 }} />
              <Box>
                <Typography variant="body2" fontWeight="medium">
                  How it works:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • Runs every hour when enabled<br />
                  • Keeps the 3 most recent files on the TV<br />
                  • Deletes older files to free up memory<br />
                  • Helps prevent TV crashes due to memory constraints
                </Typography>
              </Box>
            </Stack>
          </Box>

          <Divider sx={{ my: 2 }} />

          <Stack direction="row" spacing={2} alignItems="center">
            <Button
              variant="outlined"
              onClick={handleManualCleanup}
              disabled={cleaningUp}
              startIcon={cleaningUp ? <CircularProgress size={16} /> : <CleaningServicesIcon />}
            >
              {cleaningUp ? 'Cleaning...' : 'Run Cleanup Now'}
            </Button>
            <Typography variant="body2" color="text.secondary">
              Manually trigger cleanup to remove old files immediately
            </Typography>
          </Stack>
        </Paper>

        {/* Additional Info */}
        <Box sx={{ p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary">
            <strong>Note:</strong> These settings help maintain optimal performance of your Samsung Frame TV
            by preventing memory-related crashes during slideshow operations.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default Settings;
