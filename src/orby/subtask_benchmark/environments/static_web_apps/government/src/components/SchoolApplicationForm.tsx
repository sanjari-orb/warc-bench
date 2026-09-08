import React, { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Radio,
  RadioGroup,
  FormLabel,
  Container,
  Divider,
} from '@mui/material';

const grades = [
  'PreK',
  'Kindergarten',
  '1st Grade',
  '2nd Grade',
  '3rd Grade',
  '4th Grade',
  '5th Grade',
  '6th Grade',
  '7th Grade',
  '8th Grade',
  '9th Grade',
  '10th Grade',
  '11th Grade',
  '12th Grade',
];

const races = [
  'American Indian or Alaska Native',
  'Asian',
  'Black or African American',
  'Hispanic or Latino',
  'Native Hawaiian or Other Pacific Islander',
  'White',
  'Two or More Races',
  'Prefer not to say',
];

const SchoolApplicationForm: React.FC = () => {
  const [formData, setFormData] = useState({
    // School Information
    schoolName: '',
    applyingForGrade: '',
    
    // Student Information
    studentFirstName: '',
    studentLastName: '',
    dateOfBirth: '',
    gender: '',
    race: '',
    currentSchool: '',
    currentGrade: '',
    
    // Parent/Guardian Information
    parent1FirstName: '',
    parent1LastName: '',
    parent1Relationship: '',
    parent1Occupation: '',
    parent1Employer: '',
    parent1Phone: '',
    parent1Email: '',
    
    parent2FirstName: '',
    parent2LastName: '',
    parent2Relationship: '',
    parent2Occupation: '',
    parent2Employer: '',
    parent2Phone: '',
    parent2Email: '',
    
    // Address Information
    streetAddress: '',
    city: '',
    state: '',
    zipCode: '',
    
    // Academic History
    previousSchool1: '',
    previousSchool1Grade: '',
    previousSchool1Year: '',
    previousSchool1GPA: '',
    
    previousSchool2: '',
    previousSchool2Grade: '',
    previousSchool2Year: '',
    previousSchool2GPA: '',
    
    previousSchool3: '',
    previousSchool3Grade: '',
    previousSchool3Year: '',
    previousSchool3GPA: '',
    
    // Additional Information
    specialNeeds: '',
    specialNeedsDescription: '',
    extracurricularActivities: '',
    awardsAndAchievements: '',
    emergencyContactName: '',
    emergencyContactPhone: '',
    emergencyContactRelationship: '',
  });

  const [errors, setErrors] = useState({
    schoolName: false,
    studentFirstName: false,
    studentLastName: false,
    dateOfBirth: false,
    gender: false,
    race: false,
    parent1FirstName: false,
    parent1LastName: false,
    parent1Email: false,
    parent1Phone: false,
    streetAddress: false,
    city: false,
    state: false,
    zipCode: false,
  });

  const handleChange = (field: string) => (event: any) => {
    setFormData({
      ...formData,
      [field]: event.target.value,
    });
    setErrors({
      ...errors,
      [field]: false,
    });
  };

  const validateForm = () => {
    const newErrors = {
      schoolName: !formData.schoolName,
      studentFirstName: !formData.studentFirstName,
      studentLastName: !formData.studentLastName,
      dateOfBirth: !formData.dateOfBirth,
      gender: !formData.gender,
      race: !formData.race,
      parent1FirstName: !formData.parent1FirstName,
      parent1LastName: !formData.parent1LastName,
      parent1Email: !formData.parent1Email,
      parent1Phone: !formData.parent1Phone,
      streetAddress: !formData.streetAddress,
      city: !formData.city,
      state: !formData.state,
      zipCode: !formData.zipCode,
    };
    setErrors(newErrors);
    return !Object.values(newErrors).some((error) => error);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (validateForm()) {
      // Handle form submission
      console.log('Form submitted:', formData);
    }
  };

  return (
    <Container maxWidth="md">
      <Box py={4}>
        <Typography variant="h4" gutterBottom>
          School Application Form
        </Typography>
        <Paper elevation={2} sx={{ p: 3 }}>
          <form onSubmit={handleSubmit}>
            {/* School Information */}
            <Typography variant="h6" gutterBottom>
              School Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="School Name"
                  value={formData.schoolName}
                  onChange={handleChange('schoolName')}
                  error={errors.schoolName}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Applying for Grade</InputLabel>
                  <Select
                    value={formData.applyingForGrade}
                    onChange={handleChange('applyingForGrade')}
                    label="Applying for Grade"
                  >
                    {grades.map((grade) => (
                      <MenuItem key={grade} value={grade}>
                        {grade}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Student Information */}
            <Typography variant="h6" gutterBottom>
              Student Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Student First Name"
                  value={formData.studentFirstName}
                  onChange={handleChange('studentFirstName')}
                  error={errors.studentFirstName}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Student Last Name"
                  value={formData.studentLastName}
                  onChange={handleChange('studentLastName')}
                  error={errors.studentLastName}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Date of Birth"
                  type="date"
                  value={formData.dateOfBirth}
                  onChange={handleChange('dateOfBirth')}
                  error={errors.dateOfBirth}
                  required
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <FormLabel>Gender</FormLabel>
                  <RadioGroup
                    row
                    value={formData.gender}
                    onChange={handleChange('gender')}
                  >
                    <FormControlLabel value="male" control={<Radio />} label="Male" />
                    <FormControlLabel value="female" control={<Radio />} label="Female" />
                    <FormControlLabel value="other" control={<Radio />} label="Other" />
                  </RadioGroup>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <FormControl fullWidth>
                  <InputLabel>Race/Ethnicity</InputLabel>
                  <Select
                    value={formData.race}
                    onChange={handleChange('race')}
                    label="Race/Ethnicity"
                    error={errors.race}
                    required
                  >
                    {races.map((race) => (
                      <MenuItem key={race} value={race}>
                        {race}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Parent/Guardian Information */}
            <Typography variant="h6" gutterBottom>
              Parent/Guardian Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Parent/Guardian First Name"
                  value={formData.parent1FirstName}
                  onChange={handleChange('parent1FirstName')}
                  error={errors.parent1FirstName}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Parent/Guardian Last Name"
                  value={formData.parent1LastName}
                  onChange={handleChange('parent1LastName')}
                  error={errors.parent1LastName}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Relationship to Student"
                  value={formData.parent1Relationship}
                  onChange={handleChange('parent1Relationship')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Occupation"
                  value={formData.parent1Occupation}
                  onChange={handleChange('parent1Occupation')}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Employer"
                  value={formData.parent1Employer}
                  onChange={handleChange('parent1Employer')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Phone Number"
                  value={formData.parent1Phone}
                  onChange={handleChange('parent1Phone')}
                  error={errors.parent1Phone}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  value={formData.parent1Email}
                  onChange={handleChange('parent1Email')}
                  error={errors.parent1Email}
                  required
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Address Information */}
            <Typography variant="h6" gutterBottom>
              Address Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Street Address"
                  value={formData.streetAddress}
                  onChange={handleChange('streetAddress')}
                  error={errors.streetAddress}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="City"
                  value={formData.city}
                  onChange={handleChange('city')}
                  error={errors.city}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="State"
                  value={formData.state}
                  onChange={handleChange('state')}
                  error={errors.state}
                  required
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="ZIP Code"
                  value={formData.zipCode}
                  onChange={handleChange('zipCode')}
                  error={errors.zipCode}
                  required
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Academic History */}
            <Typography variant="h6" gutterBottom>
              Academic History
            </Typography>
            <Grid container spacing={2}>
              {[1, 2, 3].map((num) => (
                <React.Fragment key={num}>
                  <Grid item xs={12}>
                    <Typography variant="subtitle1" gutterBottom>
                      Previous School {num}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="School Name"
                      value={formData[`previousSchool${num}` as keyof typeof formData]}
                      onChange={handleChange(`previousSchool${num}`)}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Grade"
                      value={formData[`previousSchool${num}Grade` as keyof typeof formData]}
                      onChange={handleChange(`previousSchool${num}Grade`)}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Year"
                      value={formData[`previousSchool${num}Year` as keyof typeof formData]}
                      onChange={handleChange(`previousSchool${num}Year`)}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="GPA"
                      value={formData[`previousSchool${num}GPA` as keyof typeof formData]}
                      onChange={handleChange(`previousSchool${num}GPA`)}
                    />
                  </Grid>
                </React.Fragment>
              ))}
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Additional Information */}
            <Typography variant="h6" gutterBottom>
              Additional Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Special Needs (if any)"
                  value={formData.specialNeeds}
                  onChange={handleChange('specialNeeds')}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Special Needs Description"
                  value={formData.specialNeedsDescription}
                  onChange={handleChange('specialNeedsDescription')}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Extracurricular Activities"
                  value={formData.extracurricularActivities}
                  onChange={handleChange('extracurricularActivities')}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Awards and Achievements"
                  value={formData.awardsAndAchievements}
                  onChange={handleChange('awardsAndAchievements')}
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Emergency Contact */}
            <Typography variant="h6" gutterBottom>
              Emergency Contact
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Emergency Contact Name"
                  value={formData.emergencyContactName}
                  onChange={handleChange('emergencyContactName')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Emergency Contact Phone"
                  value={formData.emergencyContactPhone}
                  onChange={handleChange('emergencyContactPhone')}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Relationship to Student"
                  value={formData.emergencyContactRelationship}
                  onChange={handleChange('emergencyContactRelationship')}
                />
              </Grid>
            </Grid>

            <Box mt={4}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                size="large"
                fullWidth
              >
                Submit Application
              </Button>
            </Box>
          </form>
        </Paper>
      </Box>
    </Container>
  );
};

export default SchoolApplicationForm; 