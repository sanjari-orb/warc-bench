import React from 'react';
import { Container, Typography } from '@mui/material';

const AccountPage: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Account Settings
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Your account settings and preferences will be displayed here.
      </Typography>
    </Container>
  );
};

export default AccountPage; 