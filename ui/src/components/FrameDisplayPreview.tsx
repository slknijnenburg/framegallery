import { Box, CardMedia, Paper } from '@mui/material';
import React from 'react';

interface FrameDisplayPreviewProps {
  imageUrl: string;
}

export default function FrameDisplayPreview(props: FrameDisplayPreviewProps) {
  return (
    <Box
      sx={{
        maxWidth: 'lg',
        width: '100%',
        mx: 'auto', // centers the component
      }}
    >
      <Paper
        elevation={3}
        sx={{
          bgcolor: 'black',
          p: 1,
          border: '1px solid rgba(255, 255, 255, 0.12)',
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
              width: '100%',
              height: '100%',
              objectFit: 'contain',
            }}
          />
        </Box>
      </Paper>
    </Box>
  );
}
