import React, { useState } from 'react';
import {
  Box,
  TextField,
  Typography,
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';

interface TaxFormProps {
  formType: 'property' | 'business';
}

const states = [
  'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California',
  'Colorado', 'Connecticut', 'Delaware', 'Florida', 'Georgia',
  'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
  'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland',
  'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri',
  'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey',
  'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
  'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina',
  'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
  'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming'
];

const TaxForm: React.FC<TaxFormProps> = ({ formType }) => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    address: '',
    state: '',
    zipcode: '',
    apn: '',
  });

  const [errors, setErrors] = useState({
    address: false,
    state: false,
    zipcode: false,
    apn: false,
  });

  const [errorMessages, setErrorMessages] = useState({
    address: '',
    zipcode: '',
    apn: '',
  });

  const validateZipcode = (zip: string) => {
    const zipRegex = /^\d{5}$/;
    return zipRegex.test(zip);
  };

  const validateAPN = (apn: string) => {
    const apnRegex = /^[A-Za-z0-9]{10}$/;
    return apnRegex.test(apn);
  };

  const handleChange = (field: string) => (event: any) => {
    const value = event.target.value;
    setFormData({
      ...formData,
      [field]: value,
    });

    // Clear error when user starts typing
    setErrors({
      ...errors,
      [field]: false,
    });
    setErrorMessages({
      ...errorMessages,
      [field]: '',
    });
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (validateForm()) {
      // Navigate to the tax information display page with the APN
      navigate('/tax/information', {
        state: {
          apn: formData.apn,
          formType: formType
        }
      });
    }
  };

  const validateForm = () => {
    let isValid = true;
    const newErrors = { ...errors };
    const newErrorMessages = { ...errorMessages };

    // Validate address
    if (!formData.address.trim()) {
      newErrors.address = true;
      newErrorMessages.address = 'Address is required';
      isValid = false;
    }

    // Validate state
    if (!formData.state) {
      newErrors.state = true;
      isValid = false;
    }

    // Validate zipcode
    if (!validateZipcode(formData.zipcode)) {
      newErrors.zipcode = true;
      newErrorMessages.zipcode = 'Zipcode must be a 5-digit number';
      isValid = false;
    }

    // Validate APN
    if (!validateAPN(formData.apn)) {
      newErrors.apn = true;
      newErrorMessages.apn = 'APN must be a 10-character alphanumeric string';
      isValid = false;
    }

    setErrors(newErrors);
    setErrorMessages(newErrorMessages);

    return isValid;
  };

  const menuProps = {
    PaperProps: {
      style: {
        maxHeight: 200, // Show approximately 5 items at a time
      },
    },
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4, p: 3 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          {formType === 'property' ? 'Property Tax' : 'Business Tax'} Information
        </Typography>
        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label={`${formType === 'property' ? 'Home' : 'Business'} Address`}
                value={formData.address}
                onChange={handleChange('address')}
                error={errors.address}
                helperText={errorMessages.address}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth error={errors.state} required>
                <InputLabel>State</InputLabel>
                <Select
                  value={formData.state}
                  onChange={handleChange('state')}
                  label="State"
                  MenuProps={menuProps}
                >
                  {states.map((state) => (
                    <MenuItem key={state} value={state}>
                      {state}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Zipcode"
                value={formData.zipcode}
                onChange={handleChange('zipcode')}
                error={errors.zipcode}
                helperText={errorMessages.zipcode}
                inputProps={{ maxLength: 5 }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="APN Number"
                value={formData.apn}
                onChange={handleChange('apn')}
                error={errors.apn}
                helperText={errorMessages.apn}
                inputProps={{ maxLength: 10 }}
                required
              />
            </Grid>
            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                fullWidth
                size="large"
              >
                Submit {formType === 'property' ? 'Property' : 'Business'} Tax Information
              </Button>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Box>
  );
};

export default TaxForm; 