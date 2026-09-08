import React, { useState } from 'react';
import { Box, CssBaseline, AppBar, Toolbar, IconButton, Typography, Container, Badge, Menu, MenuItem, ListItemText, ListItemIcon, Divider, Tooltip, GlobalStyles } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircle from '@mui/icons-material/AccountCircle';
import Settings from '@mui/icons-material/Settings';
import NotificationsIcon from '@mui/icons-material/Notifications';
import HelpIcon from '@mui/icons-material/Help';
import SupportAgentIcon from '@mui/icons-material/SupportAgent';
import EmailIcon from '@mui/icons-material/Email';
import PhoneIcon from '@mui/icons-material/Phone';
import ChatIcon from '@mui/icons-material/Chat';
import Sidebar from './components/Sidebar';
import HomePage from './components/HomePage';
import AccountPage from './components/AccountPage';
import SettingsPage from './components/SettingsPage';
import SalesPage from './components/SalesPage';
import MarketingPage from './components/MarketingPage';
import CommercePage from './components/CommercePage';
import ClientsPage from './components/ClientsPage';
import InsurancePage from './components/InsurancePage';
import SupportPage from './components/SupportPage';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';

// Placeholder components for each route
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

// Separate component for AppBar content to use useNavigate
const AppBarContent = ({ sidebarOpen, onToggle }: { sidebarOpen: boolean; onToggle: () => void }) => {
  const navigate = useNavigate();
  const [notificationAnchor, setNotificationAnchor] = useState<null | HTMLElement>(null);

  const notifications = [
    { id: 1, text: 'New campaign "Summer Sale 2024" has been created', time: '5 minutes ago' },
    { id: 2, text: 'Policy renewal reminder for client John Smith', time: '1 hour ago' },
    { id: 3, text: 'New lead assigned to your team', time: '2 hours ago' },
    { id: 4, text: 'System maintenance scheduled for tonight', time: '3 hours ago' },
    { id: 5, text: 'Monthly sales report is ready', time: '5 hours ago' },
    { id: 6, text: 'New client onboarding completed', time: '1 day ago' },
    { id: 7, text: 'Marketing campaign performance report available', time: '2 days ago', link: '/marketing' },
  ];

  const handleNotificationClick = (event: React.MouseEvent<HTMLElement>) => {
    setNotificationAnchor(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchor(null);
  };

  const handleNotificationItemClick = (notification: typeof notifications[0]) => {
    handleNotificationClose();
    if (notification.link) {
      navigate(notification.link);
    }
  };

  return (
    <AppBar
      position="fixed"
      sx={{
        width: { sm: `calc(100% - ${sidebarOpen ? 240 : 0}px)` },
        ml: { sm: `${sidebarOpen ? 240 : 0}px` },
      }}
    >
      <Toolbar>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onToggle}
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
          Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Notifications">
            <IconButton
              color="inherit"
              onClick={handleNotificationClick}
              size="large"
            >
              <Badge badgeContent={7} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>
          <Tooltip title="Support">
            <IconButton
              color="inherit"
              onClick={() => navigate('/support')}
              size="large"
            >
              <HelpIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Account">
            <IconButton
              color="inherit"
              onClick={() => navigate('/account')}
              size="large"
            >
              <AccountCircle />
            </IconButton>
          </Tooltip>
          <Tooltip title="Settings">
            <IconButton
              color="inherit"
              onClick={() => navigate('/settings')}
              size="large"
            >
              <Settings />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>

      {/* Notifications Menu */}
      <Menu
        anchorEl={notificationAnchor}
        open={Boolean(notificationAnchor)}
        onClose={handleNotificationClose}
        PaperProps={{
          style: {
            maxHeight: 400,
            width: 360,
          },
        }}
      >
        <MenuItem>
          <Typography variant="h6">Notifications</Typography>
        </MenuItem>
        <Divider />
        {notifications.map((notification) => (
          <MenuItem 
            key={notification.id} 
            onClick={() => handleNotificationItemClick(notification)}
            sx={{ 
              py: 1,
              whiteSpace: 'normal',
              minHeight: 'unset',
              cursor: notification.link ? 'pointer' : 'default'
            }}
          >
            <ListItemText
              primary={notification.text}
              secondary={notification.time}
              primaryTypographyProps={{
                style: { 
                  fontSize: '0.8rem',
                  lineHeight: 1.3,
                  marginBottom: '4px',
                  color: notification.link ? 'primary.main' : 'text.primary'
                }
              }}
              secondaryTypographyProps={{
                style: { 
                  fontSize: '0.7rem',
                  lineHeight: 1.2
                }
              }}
            />
          </MenuItem>
        ))}
      </Menu>
    </AppBar>
  );
};

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleDrawerToggle = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <Router>
      <GlobalStyles
        styles={{
          html: { maxWidth: '100vw', overflowX: 'hidden' },
          body: { maxWidth: '100vw', overflowX: 'hidden' },
          '#root': { maxWidth: '100vw', overflowX: 'hidden' }
        }}
      />
      <Box sx={{ 
        display: 'flex',
        maxWidth: '100vw',
        overflowX: 'hidden'
      }}>
        <CssBaseline />
        <AppBarContent sidebarOpen={sidebarOpen} onToggle={handleDrawerToggle} />
        <Sidebar open={sidebarOpen} onToggle={handleDrawerToggle} />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            width: { sm: `calc(100% - ${sidebarOpen ? 240 : 0}px)` },
            ml: { sm: `${sidebarOpen ? 240 : 0}px` },
            maxWidth: '100vw',
            overflowX: 'hidden'
          }}
        >
          <Toolbar />
          <Routes>
            <Route path="/home" element={<HomePage />} />
            <Route path="/account" element={<AccountPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/sales" element={<SalesPage />} />
            <Route path="/marketing" element={<MarketingPage />} />
            <Route path="/commerce" element={<CommercePage />} />
            <Route path="/clients" element={<ClientsPage />} />
            <Route path="/insurance" element={<InsurancePage />} />
            <Route path="/support" element={<SupportPage />} />
            <Route path="/" element={<Navigate to="/home" replace />} />
          </Routes>
        </Box>
      </Box>
    </Router>
  );
}

export default App;