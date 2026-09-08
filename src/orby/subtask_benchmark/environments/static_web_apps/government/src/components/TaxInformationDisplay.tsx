import React from 'react';
import { Box, Typography, Container, Paper, Grid } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';

interface TaxInformation {
  apn: string;
  taxDue: number;
  dueDate: string;
  delinquentAfter: string;
}

const TaxInformationDisplay: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { apn, formType } = location.state as { apn: string; formType: 'property' | 'business' };

  // Generate random tax information
  const taxInfo: TaxInformation = {
    apn,
    taxDue: Math.floor(Math.random() * 10000) + 1000, // Random amount between 1000 and 11000
    dueDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString(), // 30 days from now
    delinquentAfter: new Date(Date.now() + 45 * 24 * 60 * 60 * 1000).toLocaleDateString(), // 45 days from now
  };

  const handleBack = () => {
    navigate(formType === 'property' ? '/tax/property' : '/tax/business');
  };

  return (
    <Container maxWidth="md">
      <Box py={4}>
        <Typography variant="h4" gutterBottom>
          {formType === 'property' ? 'Property' : 'Business'} Tax Information
        </Typography>
        <Paper elevation={2} sx={{ p: 3, mt: 2 }}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" color="primary">
                APN: {taxInfo.apn}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle1" color="text.secondary">
                Tax Due
              </Typography>
              <Typography variant="h5">
                ${taxInfo.taxDue.toLocaleString()}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle1" color="text.secondary">
                Due Date
              </Typography>
              <Typography variant="h5">
                {taxInfo.dueDate}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle1" color="text.secondary">
                Delinquent After
              </Typography>
              <Typography variant="h5" color="error">
                {taxInfo.delinquentAfter}
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      </Box>
    </Container>
  );
};

export default TaxInformationDisplay; 