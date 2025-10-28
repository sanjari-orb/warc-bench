import React from 'react';
import { Container, Typography } from '@mui/material';

const SettingsPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        System Settings
      </Typography>
      <Typography variant="body1" color="text.secondary">
        System configuration and settings will be displayed here.
      </Typography>
    </Container>
  );
};

export default SettingsPage; 