import React from 'react';
import { Container, Typography } from '@mui/material';

const HomePage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Home Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Welcome to your dashboard. Your home content will be displayed here.
      </Typography>
    </Container>
  );
};

export default HomePage; 