import React from 'react';
import { Box, Typography, Container, Paper } from '@mui/material';
import TaxForm from './TaxForm.tsx';

const PropertyTaxPage: React.FC = () => {
  return (
    <Container maxWidth="md">
      <Box py={4}>
        <Typography variant="h4" gutterBottom>
          Property Tax Information
        </Typography>
        <Typography variant="body1" paragraph>
          Enter your property information below to retrieve your tax details.
        </Typography>
        <Paper elevation={2} sx={{ p: 3 }}>
          <TaxForm formType="property" />
        </Paper>
      </Box>
    </Container>
  );
};

export default PropertyTaxPage; 