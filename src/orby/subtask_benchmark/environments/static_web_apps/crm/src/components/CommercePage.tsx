import React from 'react';
import { Container, Typography } from '@mui/material';

const CommercePage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Commerce Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Your commerce and transaction data will be displayed here.
      </Typography>
    </Container>
  );
};

export default CommercePage; 