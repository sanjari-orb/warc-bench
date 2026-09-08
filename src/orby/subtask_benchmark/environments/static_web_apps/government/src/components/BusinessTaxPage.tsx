import React from 'react';
import { Box, Typography, Container, Paper } from '@mui/material';
import TaxForm from './TaxForm.tsx';

const BusinessTaxPage: React.FC = () => {
  return (
    <Container maxWidth="md">
      <Box py={4}>
        <Typography variant="h4" gutterBottom>
          Business Tax Information
        </Typography>
        <Typography variant="body1" paragraph>
          Enter your business information below to retrieve your tax details.
        </Typography>
        <Paper elevation={2} sx={{ p: 3 }}>
          <TaxForm formType="business" />
        </Paper>
      </Box>
    </Container>
  );
};

export default BusinessTaxPage; 