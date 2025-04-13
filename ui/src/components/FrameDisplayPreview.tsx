import { Box, CardMedia, IconButton, Paper } from '@mui/material';
import React from 'react';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import axios from 'axios';
import { API_BASE_URL } from '../App'; 
import Image from '../models/Image'; // Import the Image model

interface FrameDisplayPreviewProps {
  imageUrl: string;
  onNext?: (newImage: Image) => void; // Update prop signature to accept Image
}

export default function FrameDisplayPreview(props: FrameDisplayPreviewProps) {

  const handleNextClick = async () => {
    try {
      // Make the POST request and expect an Image object in response
      const response = await axios.post<Image>(`${API_BASE_URL}/api/images/next`); 
      // Pass the received image data to the callback
      if (props.onNext) {
        props.onNext(response.data);
      }
    } catch (error) {
      console.error('Error fetching next image:', error);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex', // Use flexbox to align items
        alignItems: 'center', // Center items vertically
        justifyContent: 'center', // Center items horizontally
        maxWidth: 'lg',
        width: '100%',
        mx: 'auto',
      }}
    >
      <Box sx={{ flexGrow: 1, maxWidth: '90%' }}> {/* Container for the frame preview, allow shrinking */}
        <Paper
          elevation={3}
          sx={{
            bgcolor: 'black',
            p: 1,
            border: '1px solid rgba(255, 255, 255, 0.12)',
            width: '100%', // Make paper take full width of its container
          }}
        >
          <Box
            sx={{
              position: 'relative',
              paddingTop: '56.25%', // 16:9 aspect ratio
            }}
          >
            <CardMedia
              component="img"
              image={props.imageUrl}
              sx={{
                position: 'absolute',
                top: 0,
                left: 0, // Added left: 0 for absolute positioning
                width: '100%',
                height: '100%',
                objectFit: 'contain',
              }}
            />
          </Box>
        </Paper>
      </Box>
      <IconButton
        onClick={handleNextClick}
        sx={{
          ml: 1, // Add some margin to the left
          color: 'white', // Set icon color
          bgcolor: 'rgba(0, 0, 0, 0.5)', // Add a subtle background
          '&:hover': {
            bgcolor: 'rgba(0, 0, 0, 0.7)', // Darken background on hover
          },
        }}
        aria-label="next image"
      >
        <ArrowForwardIosIcon />
      </IconButton>
    </Box>
  );
}
