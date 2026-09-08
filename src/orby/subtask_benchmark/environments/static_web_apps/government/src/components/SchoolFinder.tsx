import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Paper,
  Grid,
  FormControlLabel,
  Radio,
  RadioGroup,
  FormLabel,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';

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

const specialNeeds = ['None', 'Autism', 'Deaf', 'Blind'];

const artPrograms = [
  'All',
  'Visual Arts',
  'Music',
  'Dance',
  'Theater',
  'Creative Writing',
  'Digital Arts',
  'Photography',
  'Ceramics',
  'Graphic Design',
];

const sports = [
  'All',
  'Basketball',
  'Football',
  'Soccer',
  'Baseball',
  'Softball',
  'Volleyball',
  'Track & Field',
  'Swimming',
  'Tennis',
  'Golf',
  'Cross Country',
  'Wrestling',
  'Cheerleading',
];

const afterSchoolPrograms = [
  'All',
  'Homework Help',
  'STEM Club',
  'Robotics',
  'Coding',
  'Chess Club',
  'Debate Team',
  'Yearbook',
  'Student Council',
  'Language Club',
];

const beforeSchoolPrograms = [
  'All',
  'Breakfast Program',
  'Morning Care',
  'Study Hall',
  'Fitness Club',
  'Reading Club',
  'Math Club',
];

const SchoolFinder: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    grade: '',
    homeAddress: '',
    specialNeeds: '',
    artPrograms: '',
    sports: '',
    afterSchoolPrograms: '',
    beforeSchoolPrograms: '',
    distanceRadius: '0-5',
    schoolRating: '1-4', // Default to 1-4 rating
  });

  const [errors, setErrors] = useState({
    grade: false,
    homeAddress: false,
    specialNeeds: false,
    artPrograms: false,
    sports: false,
    afterSchoolPrograms: false,
    beforeSchoolPrograms: false,
  });

  const menuProps = {
    PaperProps: {
      style: {
        maxHeight: 200, // This will show approximately 5 items
      },
    },
  };

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
      grade: !formData.grade,
      homeAddress: !formData.homeAddress,
      specialNeeds: !formData.specialNeeds,
      artPrograms: !formData.artPrograms,
      sports: !formData.sports,
      afterSchoolPrograms: !formData.afterSchoolPrograms,
      beforeSchoolPrograms: !formData.beforeSchoolPrograms,
    };
    setErrors(newErrors);
    return !Object.values(newErrors).some((error) => error);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (validateForm()) {
      navigate('/schools/finder/results');
    }
  };

  const handleRadioChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [event.target.name]: event.target.value,
    });
  };

  const isFormValid = Object.values(formData).every((value) => value !== '');

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4, p: 3 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          School Finder
        </Typography>
        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth error={errors.grade}>
                <InputLabel>Grade</InputLabel>
                <Select
                  value={formData.grade}
                  onChange={handleChange('grade')}
                  label="Grade"
                  MenuProps={menuProps}
                >
                  {grades.map((grade) => (
                    <MenuItem key={grade} value={grade}>
                      {grade}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth error={errors.specialNeeds}>
                <InputLabel>Special Needs</InputLabel>
                <Select
                  value={formData.specialNeeds}
                  onChange={handleChange('specialNeeds')}
                  label="Special Needs"
                  MenuProps={menuProps}
                >
                  {specialNeeds.map((need) => (
                    <MenuItem key={need} value={need}>
                      {need}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth error={errors.artPrograms}>
                <InputLabel>Arts & Enrichment Programs</InputLabel>
                <Select
                  value={formData.artPrograms}
                  onChange={handleChange('artPrograms')}
                  label="Arts & Enrichment Programs"
                  MenuProps={menuProps}
                >
                  {artPrograms.map((program) => (
                    <MenuItem key={program} value={program}>
                      {program}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth error={errors.sports}>
                <InputLabel>Sports</InputLabel>
                <Select
                  value={formData.sports}
                  onChange={handleChange('sports')}
                  label="Sports"
                  MenuProps={menuProps}
                >
                  {sports.map((sport) => (
                    <MenuItem key={sport} value={sport}>
                      {sport}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth error={errors.afterSchoolPrograms}>
                <InputLabel>After School Programs</InputLabel>
                <Select
                  value={formData.afterSchoolPrograms}
                  onChange={handleChange('afterSchoolPrograms')}
                  label="After School Programs"
                  MenuProps={menuProps}
                >
                  {afterSchoolPrograms.map((program) => (
                    <MenuItem key={program} value={program}>
                      {program}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth error={errors.beforeSchoolPrograms}>
                <InputLabel>Before School Programs</InputLabel>
                <Select
                  value={formData.beforeSchoolPrograms}
                  onChange={handleChange('beforeSchoolPrograms')}
                  label="Before School Programs"
                  MenuProps={menuProps}
                >
                  {beforeSchoolPrograms.map((program) => (
                    <MenuItem key={program} value={program}>
                      {program}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Home Address"
                value={formData.homeAddress}
                onChange={handleChange('homeAddress')}
                error={errors.homeAddress}
                helperText={errors.homeAddress ? 'Please enter your home address' : ''}
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl component="fieldset">
                <FormLabel component="legend">Search Radius</FormLabel>
                <RadioGroup
                  row
                  name="distanceRadius"
                  value={formData.distanceRadius}
                  onChange={handleRadioChange}
                >
                  <FormControlLabel
                    value="0-5"
                    control={<Radio />}
                    label="0-5 miles"
                  />
                  <FormControlLabel
                    value="5-10"
                    control={<Radio />}
                    label="5-10 miles"
                  />
                  <FormControlLabel
                    value="10+"
                    control={<Radio />}
                    label="More than 10 miles"
                  />
                </RadioGroup>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <FormControl component="fieldset">
                <FormLabel component="legend">School Rating</FormLabel>
                <RadioGroup
                  row
                  name="schoolRating"
                  value={formData.schoolRating}
                  onChange={handleRadioChange}
                >
                  <FormControlLabel
                    value="1-4"
                    control={<Radio />}
                    label="1-4 Rating"
                  />
                  <FormControlLabel
                    value="4-7"
                    control={<Radio />}
                    label="4-7 Rating"
                  />
                  <FormControlLabel
                    value="7-10"
                    control={<Radio />}
                    label="7-10 Rating"
                  />
                </RadioGroup>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                color="primary"
                fullWidth
                size="large"
                disabled={!isFormValid}
                sx={{ mt: 2 }}
              >
                Search Schools
              </Button>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Box>
  );
};

export default SchoolFinder; 