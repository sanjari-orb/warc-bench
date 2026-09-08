import React from 'react';
import {
  Container,
  Typography,
  Grid,
  Paper,
  IconButton,
  Box,
  Link,
  Button,
} from '@mui/material';
import {
  Phone as PhoneIcon,
  Email as EmailIcon,
  Chat as ChatIcon,
} from '@mui/icons-material';

const SupportPage: React.FC = () => {
  const handleCallClick = () => {
    window.location.href = 'tel:+1-800-123-4567';
  };

  const handleEmailClick = () => {
    window.location.href = 'mailto:support@example.com';
  };

  const handleChatClick = () => {
    // Implement chat functionality
    console.log('Starting chat...');
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Customer Support
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Choose your preferred way to contact our support team
      </Typography>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' }, gap: 3 }}>
        <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', p: 3 }}>
          <IconButton
            size="large"
            color="primary"
            onClick={handleCallClick}
            sx={{ mb: 2 }}
          >
            <PhoneIcon fontSize="large" />
          </IconButton>
          <Typography variant="h6" gutterBottom>
            Call Us
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" paragraph>
            Speak directly with our support team
          </Typography>
          <Link
            href="tel:+1-800-123-4567"
            color="primary"
            sx={{ mt: 2 }}
          >
            +1-800-123-4567
          </Link>
        </Paper>

        <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', p: 3 }}>
          <IconButton
            size="large"
            color="primary"
            onClick={handleEmailClick}
            sx={{ mb: 2 }}
          >
            <EmailIcon fontSize="large" />
          </IconButton>
          <Typography variant="h6" gutterBottom>
            Email Us
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" paragraph>
            Send us an email and we'll get back to you
          </Typography>
          <Link
            href="mailto:support@example.com"
            color="primary"
            sx={{ mt: 2 }}
          >
            support@example.com
          </Link>
        </Paper>

        <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', p: 3 }}>
          <IconButton
            size="large"
            color="primary"
            onClick={handleChatClick}
            sx={{ mb: 2 }}
          >
            <ChatIcon fontSize="large" />
          </IconButton>
          <Typography variant="h6" gutterBottom>
            Live Chat
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" paragraph>
            Chat with our support team in real-time
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={handleChatClick}
            sx={{ mt: 2 }}
          >
            Start Chat
          </Button>
        </Paper>
      </Box>
    </Container>
  );
};

export default SupportPage; 