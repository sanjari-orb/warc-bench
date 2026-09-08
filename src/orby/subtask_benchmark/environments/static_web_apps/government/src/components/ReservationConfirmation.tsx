import React from 'react';
import {
  Container,
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Divider,
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

const ReservationConfirmation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { spotName, selectedDate, selectedSlots, totalCost, paymentDetails } = location.state;

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const generateConfirmationNumber = () => {
    return `PIC-${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4, textAlign: 'center' }}>
        <CheckCircleIcon color="success" sx={{ fontSize: 80, mb: 2 }} />
        <Typography variant="h4" color="success.main" gutterBottom>
          Reservation Confirmed!
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Your picnic spot has been successfully reserved
        </Typography>

        <Paper elevation={2} sx={{ p: 3, mt: 4 }}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Reservation Details
              </Typography>
              <Divider sx={{ mb: 2 }} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Confirmation Number
              </Typography>
              <Typography variant="body1" gutterBottom>
                {generateConfirmationNumber()}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Location
              </Typography>
              <Typography variant="body1" gutterBottom>
                {spotName}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Date
              </Typography>
              <Typography variant="body1" gutterBottom>
                {formatDate(new Date(selectedDate))}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Time Slots
              </Typography>
              <Typography variant="body1" gutterBottom>
                {selectedSlots.map((slot: any) => `${slot.start} - ${slot.end}`).join(', ')}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Total Cost
              </Typography>
              <Typography variant="body1" gutterBottom>
                ${totalCost}
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="subtitle2" color="text.secondary">
                Payment Method
              </Typography>
              <Typography variant="body1" gutterBottom>
                Card ending in {paymentDetails.cardNumber.slice(-4)}
              </Typography>
            </Grid>
          </Grid>

          <Box sx={{ mt: 4 }}>
            <Typography variant="body2" color="text.secondary" paragraph>
              A confirmation email has been sent to your registered email address with all the details.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Please arrive 15 minutes before your reservation time. Don't forget to bring your confirmation number.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              In case of any changes or cancellations, please contact our support team at least 24 hours before your reservation.
            </Typography>
          </Box>

          <Box sx={{ mt: 4, display: 'flex', justifyContent: 'center', gap: 2 }}>
            <Button
              variant="contained"
              color="primary"
              onClick={() => navigate('/parks/picnic')}
            >
              Book Another Spot
            </Button>
            <Button
              variant="outlined"
              color="primary"
              onClick={() => window.print()}
            >
              Print Confirmation
            </Button>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default ReservationConfirmation; 