import React, { useEffect, useState } from 'react';
import { Paper, Stack, ToggleButton, ToggleButtonGroup } from '@mui/material';
import { styled } from '@mui/material/styles';
import { disableSlideshow, enableSlideshow } from '../actions/slideshow';
import { API_BASE_URL } from '../App';

export interface SlideshowStatus {
  enabled: boolean;
  interval: Number;
}

export interface StatusBarProps {
  tv_on: boolean;
  art_mode_supported: boolean;
  art_mode_active: boolean;
  api_version: string;
}

const Item = styled(Paper)(({ theme }) => ({
  backgroundColor: '#fff',
  ...theme.typography.body2,
  padding: theme.spacing(1),
  textAlign: 'center',
  color: theme.palette.text.secondary,
  ...theme.applyStyles('dark', {
    backgroundColor: '#1A2027',
  }),
}));

function StatusBar({ tv_on, art_mode_supported, art_mode_active, api_version }: StatusBarProps) {
  const [slideshowStatus, setSlideshowStatus] = useState(false);
  const [isFirstLoad, setIsFirstLoad] = useState(true); // Track initial load

  // Load initial toggle status from backend on component mount
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/slideshow`);
        const data: SlideshowStatus = await response.json();
        console.log('slideshow data = ', data);
        // `value` is either "off" or the slideshow interval in minutes.
        setSlideshowStatus(data.enabled);
        setIsFirstLoad(false); // Set to false after initial load
      } catch (error) {
        console.error('Error fetching status:', error);
      }
    };

    fetchStatus();
  }, []);

  // Handle status change (when user toggles the switch)
  const handleToggleChange = async (event: React.MouseEvent<HTMLElement>, newStatus: 'on' | 'off') => {
    console.log('New slideshow status: ', newStatus);
    setSlideshowStatus(newStatus === 'on'); // Update toggle UI

    if (!isFirstLoad) {
      try {
        if (newStatus === 'on') {
          await enableSlideshow();
        } else {
          await disableSlideshow();
        }
      } catch (error) {
        console.error('Error updating slideshow status:', error);
      }
    }
  };

  return (
    <>
      <Stack direction={'row'} justifyContent={'space-evenly'} spacing={2}>
        <div>
          <h2>Status</h2>
          <Stack direction="row" spacing={2}>
            <Item>TV: {tv_on ? 'On' : 'Off'}</Item>
            <Item>Art Mode: {art_mode_supported ? (art_mode_active ? 'On' : 'Off') : 'Not Supported'}</Item>
            <Item>API Version: {api_version}</Item>
          </Stack>
        </div>
        <div>
          <h2>Slideshow</h2>
          Status: &nbsp;
          <ToggleButtonGroup
            exclusive
            onChange={handleToggleChange}
            aria-label="Slideshow"
            value={slideshowStatus ? 'on' : 'off'}
          >
            <ToggleButton value="on">On</ToggleButton>
            <ToggleButton value="off">Off</ToggleButton>
          </ToggleButtonGroup>
        </div>
      </Stack>
    </>
  );
}

export default StatusBar;
