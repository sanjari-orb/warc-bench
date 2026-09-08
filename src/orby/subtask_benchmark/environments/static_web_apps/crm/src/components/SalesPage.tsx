import React from 'react';
import { Container, Typography } from '@mui/material';

const SalesPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Sales Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Your sales metrics and analytics will be displayed here.
      </Typography>
    </Container>
  );
};

export default SalesPage; 