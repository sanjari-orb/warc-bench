import React, { useState, useRef, useEffect } from 'react';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Box, 
  Button, 
  Container,
  CssBaseline,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  CardActions,
  Grid,
  Paper
} from '@mui/material';
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom';
import SchoolFinder from './components/SchoolFinder.tsx';
import SchoolFinderResults from './components/SchoolFinderResults.tsx';
import SchoolApplicationForm from './components/SchoolApplicationForm.tsx';
import PropertyTaxPage from './components/PropertyTaxPage.tsx';
import BusinessTaxPage from './components/BusinessTaxPage.tsx';
import TaxInformationDisplay from './components/TaxInformationDisplay.tsx';
import {
  School as SchoolIcon,
  AccountBalance as TaxIcon,
  Park as ParkIcon,
  Description as RecordsIcon
} from '@mui/icons-material';
import { 
  Notifications as NotificationsIcon,
  Help as HelpIcon,
  AccountCircle,
  Settings,
} from '@mui/icons-material';
import PoliceDepartmentRecords from './components/PoliceDepartmentRecords.tsx';
import PicnicSpots from './components/PicnicSpots.tsx';
import PicnicReservation from './components/PicnicReservation.tsx';
import PaymentForm from './components/PaymentForm.tsx';
import ReservationConfirmation from './components/ReservationConfirmation.tsx';
import ParksAndTrails from './components/ParksAndTrails.tsx';

// Placeholder pages for each route
const PlaceholderPage = ({ title }: { title: string }) => (
  <Container>
    <Typography variant="h4" component="h1" gutterBottom>
      {title}
    </Typography>
    <Typography paragraph>
      This is a placeholder page for {title}. Content will be added later.
    </Typography>
  </Container>
);

// Menu items with their submenus
const menuItems = [
  {
    name: 'Schools',
    icon: <SchoolIcon />,
    submenu: [
      { name: 'School Finder', path: '/schools/finder' },
      { name: 'School Application Form', path: '/schools/application' },
    ],
  },
  {
    name: 'Tax',
    icon: <TaxIcon />,
    submenu: [
      { name: 'Property Tax', path: '/tax/property' },
      { name: 'Business Tax', path: '/tax/business' },
    ],
  },
  {
    name: 'Recreation',
    icon: <ParkIcon />,
    submenu: [
      { name: 'Picnic Reservation', path: '/recreation/reservations' },
      { name: 'Parks and Trails', path: '/recreation/parks' }
    ]
  },
  {
    name: 'Public Records',
    icon: <RecordsIcon />,
    submenu: [
      { name: 'Police Department', path: '/records/police' },
      { name: 'Fire Department', path: '/records/fire' }
    ]
  }
];

// Home page component
const HomePage = () => (
  <Container>
    <Typography variant="h4" component="h1" gutterBottom sx={{ mt: 4, mb: 4 }}>
      Welcome to Government Services
    </Typography>
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h5" component="h2" gutterBottom>
              School Services
            </Typography>
            <Typography variant="body1" paragraph>
              Find schools in your area and submit applications.
            </Typography>
          </CardContent>
          <CardActions>
            <Button component={Link} to="/schools/finder" variant="contained" color="primary">
              School Finder
            </Button>
            <Button component={Link} to="/schools/application" variant="outlined">
              Application Form
            </Button>
          </CardActions>
        </Card>
      </Grid>
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h5" component="h2" gutterBottom>
              Tax Services
            </Typography>
            <Typography variant="body1" paragraph>
              Access property and business tax information and forms.
            </Typography>
          </CardContent>
          <CardActions>
            <Button component={Link} to="/tax/property" variant="contained" color="primary">
              Property Tax
            </Button>
            <Button component={Link} to="/tax/business" variant="outlined">
              Business Tax
            </Button>
          </CardActions>
        </Card>
      </Grid>
    </Grid>
  </Container>
);

const App = () => {
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const menuTimeoutRef = useRef<number | null>(null);
  const submenuRef = useRef<HTMLDivElement>(null);

  const handleMenuOpen = (menuTitle: string) => {
    if (menuTimeoutRef.current) {
      window.clearTimeout(menuTimeoutRef.current);
    }
    setActiveMenu(menuTitle);
  };

  const handleMenuClose = () => {
    menuTimeoutRef.current = window.setTimeout(() => {
      setActiveMenu(null);
    }, 200); // Small delay to allow for mouse movement
  };

  const handleSubmenuEnter = () => {
    if (menuTimeoutRef.current) {
      window.clearTimeout(menuTimeoutRef.current);
    }
  };

  const handleSubmenuLeave = () => {
    menuTimeoutRef.current = window.setTimeout(() => {
      setActiveMenu(null);
    }, 200);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (menuTimeoutRef.current) {
        window.clearTimeout(menuTimeoutRef.current);
      }
    };
  }, []);

  const handleNotificationsClick = () => {
    // Implement notifications click handler
  };

  return (
    <Router>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component={Link} to="/" sx={{ 
              flexGrow: 0, 
              mr: 2, 
              color: 'inherit', 
              textDecoration: 'none' 
            }}>
              Government Services
            </Typography>
            <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center' }}>
              {menuItems.map((item) => (
                <Box
                  key={item.name}
                  sx={{ position: 'relative', mr: 2 }}
                  onMouseEnter={() => handleMenuOpen(item.name)}
                  onMouseLeave={handleMenuClose}
                >
                  <Button
                    color="inherit"
                    startIcon={item.icon}
                    sx={{ textTransform: 'none' }}
                  >
                    {item.name}
                  </Button>
                </Box>
              ))}
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Tooltip title="Notifications">
                <IconButton color="inherit" onClick={handleNotificationsClick}>
                  <NotificationsIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Support">
                <IconButton color="inherit" component={Link} to="/support">
                  <HelpIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Account">
                <IconButton color="inherit">
                  <AccountCircle />
                </IconButton>
              </Tooltip>
              <Tooltip title="Settings">
                <IconButton color="inherit">
                  <Settings />
                </IconButton>
              </Tooltip>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Submenu Bar */}
        {activeMenu && (
          <Paper 
            ref={submenuRef}
            elevation={2} 
            sx={{ 
              position: 'absolute', 
              width: '100%', 
              zIndex: 1,
              backgroundColor: 'white',
              display: 'flex',
              justifyContent: 'center',
              py: 1
            }}
            onMouseEnter={handleSubmenuEnter}
            onMouseLeave={handleSubmenuLeave}
          >
            <Box sx={{ display: 'flex', gap: 2 }}>
              {menuItems
                .find(item => item.name === activeMenu)
                ?.submenu.map((subItem) => (
                  <Button
                    key={subItem.name}
                    component={Link}
                    to={subItem.path}
                    variant="text"
                    sx={{ 
                      color: 'text.primary',
                      '&:hover': {
                        backgroundColor: 'action.hover'
                      }
                    }}
                  >
                    {subItem.name}
                  </Button>
                ))}
            </Box>
          </Paper>
        )}

        <Container sx={{ mt: 4 }}>
          <Routes>
            {/* Home Route */}
            <Route path="/" element={<HomePage />} />
            
            {/* Schools Routes */}
            <Route path="/schools/finder" element={<SchoolFinder />} />
            <Route path="/schools/finder/results" element={<SchoolFinderResults />} />
            <Route path="/schools/application" element={<SchoolApplicationForm />} />
            
            {/* Tax Routes */}
            <Route path="/tax/property" element={<PropertyTaxPage />} />
            <Route path="/tax/business" element={<BusinessTaxPage />} />
            
            {/* Tax Information Display Route */}
            <Route path="/tax/information" element={<TaxInformationDisplay />} />
            
            {/* Recreation Routes */}
            <Route path="/recreation/parks" element={<ParksAndTrails />} />
            <Route path="/recreation/reservations" element={<PicnicSpots />} />
            
            {/* Parks Routes */}
            <Route path="/parks/picnic" element={<PicnicSpots />} />
            <Route path="/parks/picnic/reservation/:spotId" element={<PicnicReservation />} />
            <Route path="/parks/playground" element={<PlaceholderPage title="Playground" />} />
            <Route path="/parks/picnic/payment" element={<PaymentForm />} />
            <Route path="/parks/picnic/confirmation" element={<ReservationConfirmation />} />
            
            {/* Public Records Routes */}
            <Route path="/records/police" element={<PoliceDepartmentRecords />} />
            <Route path="/records/fire" element={<PlaceholderPage title="Fire Department" />} />
            
            {/* Redirect any unknown routes to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Container>
      </Box>
    </Router>
  );
};

export default App; 