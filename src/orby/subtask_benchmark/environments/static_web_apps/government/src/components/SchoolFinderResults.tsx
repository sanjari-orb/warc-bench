import React from 'react';
import { Box, Typography, Paper } from '@mui/material';

const SchoolFinderResults: React.FC = () => {
  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4, p: 3 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          School Finder Results
        </Typography>
        <Typography variant="body1" align="center">
          This is a placeholder page for school finder results.
        </Typography>
      </Paper>
    </Box>
  );
};

export default SchoolFinderResults; 