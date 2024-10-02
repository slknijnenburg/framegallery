import React from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import StatusBar from "./components/StatusBar";

export default function App() {
  return (
    <Container maxWidth="sm">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" sx={{ mb: 2 }}>
          The Frame Art Gallery Manager
        </Typography>
      </Box>
      <StatusBar tv_on={true} api_version="4.2.3.0" art_mode_active={true} art_mode_supported={true} />
    </Container>
  );
}
