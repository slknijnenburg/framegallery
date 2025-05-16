import React from 'react';
import { Box, IconButton, Paper } from '@mui/material';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import axios from 'axios';
import { API_BASE_URL } from '../App'; 
import Image from '../models/Image'; 

interface FrameDisplayPreviewProps {
  imageUrl: string; 
  onNext?: (newImage: Image) => void; 
}

export default function FrameDisplayPreview(props: FrameDisplayPreviewProps) {
  const { imageUrl, onNext } = props;

  // Construct the URL for the cropped image
  const currentCroppedImageUrl = imageUrl; // Assuming imageUrl is the direct URL for the preview

  const handleNextClick = async () => {
    try {
      const response = await axios.post<Image>(`${API_BASE_URL}/api/images/next`); 
      if (onNext) {
        onNext(response.data);
      }
    } catch (error) {
      console.error('Error fetching next image:', error);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        maxWidth: 'lg',
        mx: 'auto', 
        p: 2, 
        position: 'relative', 
      }}
    >
      <Paper
        elevation={3}
        sx={{
          width: '100%',
          paddingBottom: '56.25%', 
          position: 'relative',
          overflow: 'hidden',
          backgroundColor: 'black', 
        }}
      >
        <img
          src={currentCroppedImageUrl} 
          alt="Frame Display Preview"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            objectFit: 'contain', 
          }}
        />
      </Paper>
      {onNext && (
        <IconButton
          onClick={handleNextClick}
          sx={{
            position: 'absolute',
            right: 30, 
            top: '50%',
            transform: 'translateY(-50%)',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            color: 'white',
            '&:hover': {
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
            },
          }}
          aria-label="next image"
        >
          <ArrowForwardIosIcon />
        </IconButton>
      )}
    </Box>
  );
}
