import React from 'react';
import { useSettings } from '../SettingsContext';
import { Box, Stack, Typography, CircularProgress, Paper, Tooltip } from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import FilterListIcon from '@mui/icons-material/FilterList';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';

const SettingsStatus: React.FC = () => {
  const { settings, loading, error } = useSettings();

  if (loading) {
    return <Box display="flex" justifyContent="center" alignItems="center" minHeight={56}><CircularProgress size={24} /> </Box>;
  }
  if (error) {
    return <Typography color="error">Error: {error}</Typography>;
  }
  if (!settings) {
    return null;
  }

  return (
    <Box maxWidth="lg" mx="auto" width="100%">
      <Paper elevation={2} sx={{ px: 2, py: 0.5, mb: 2, borderRadius: 2, display: 'flex', alignItems: 'center', minHeight: 44, background: 'rgba(255,255,255,0.95)' }}>
        <Stack direction="row" spacing={2} alignItems="center" width="100%" sx={{ flexWrap: 'nowrap', overflow: 'hidden' }}>

          {/* Slideshow interval */}
          <Stack direction="row" spacing={0.5} alignItems="center" minWidth={0}>
            <Tooltip title="Slideshow Interval">
              <AccessTimeIcon fontSize="small" color="action" />
            </Tooltip>
            <Typography variant="body2" noWrap>{settings.slideshow_interval} s</Typography>
          </Stack>

          {/* Slideshow enabled */}
          <Stack direction="row" spacing={0.5} alignItems="center" minWidth={0}>
            <Tooltip title="Slideshow Enabled">
              {settings.slideshow_enabled ? (
                <CheckCircleIcon color="success" fontSize="small" />
              ) : (
                <CancelIcon color="disabled" fontSize="small" />
              )}
            </Tooltip>
            <Typography variant="body2" noWrap>{settings.slideshow_enabled ? 'On' : 'Off'}</Typography>
          </Stack>

          {/* Current image */}
          <Stack direction="row" spacing={0.5} alignItems="center" minWidth={0} sx={{ flexGrow: 1, minWidth: 0 }}>
            <Tooltip title="Current Image">
              <InsertDriveFileIcon fontSize="small" color="action" />
            </Tooltip>
            <Typography
              variant="body2"
              noWrap
              title={settings.current_active_image?.filename || 'None'}
              sx={{ textOverflow: 'ellipsis', overflow: 'hidden', flexGrow: 1, minWidth: 0 }}
            >
              {settings.current_active_image?.filename || 'None'}
            </Typography>
          </Stack>

          {/* Active filter */}
          <Stack direction="row" spacing={0.5} alignItems="center" minWidth={0}>
            <Tooltip title="Active Filter">
              <FilterListIcon fontSize="small" color="action" />
            </Tooltip>
            <Typography variant="body2" noWrap>{settings.active_filter?.name || 'None'}</Typography>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  );
};

export default SettingsStatus;
