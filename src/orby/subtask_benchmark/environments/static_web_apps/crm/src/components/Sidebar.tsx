import React, { useState } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  IconButton,
  styled,
  Dialog,
  DialogTitle,
  DialogContent,
  ListItemButton,
  Divider,
} from '@mui/material';
import {
  Home as HomeIcon,
  AccountCircle as AccountIcon,
  Settings as SettingsIcon,
  ShoppingCart as SalesIcon,
  Campaign as MarketingIcon,
  // Store as CommerceIcon,
  MoreHoriz as MoreIcon,
  ChevronLeft as ChevronLeftIcon,
  Devices as DigitalExperiencesIcon,
  HomeWork as InsuranceHomepageIcon,
  Description as PolicyCenterIcon,
  Share as OutreachIcon,
  People as ClientsIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const drawerWidth = 240;

const DrawerHeader = styled('div')(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  padding: theme.spacing(0, 1),
  ...theme.mixins.toolbar,
  justifyContent: 'flex-end',
}));

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
}

const allMenuItems = [
  { text: 'Home', icon: <HomeIcon />, path: '/home' },
  { text: 'Sales', icon: <SalesIcon />, path: '/sales' },
  { text: 'Marketing', icon: <MarketingIcon />, path: '/marketing' },
  // { text: 'Commerce', icon: <CommerceIcon />, path: '/commerce' },
  { text: 'Clients', icon: <ClientsIcon />, path: '/clients' },
  { text: 'Digital Experiences', icon: <DigitalExperiencesIcon />, path: '/digital-experiences' },
  { text: 'Insurance', icon: <InsuranceHomepageIcon />, path: '/insurance' },
  { text: 'Policy Center', icon: <PolicyCenterIcon />, path: '/policy-center' },
  { text: 'Outreach', icon: <OutreachIcon />, path: '/outreach' },
];

const mainMenuItems = allMenuItems.slice(0, 6); // First 7 items for the sidebar

const Sidebar: React.FC<SidebarProps> = ({ open, onToggle }) => {
  const navigate = useNavigate();
  const [showMoreDialog, setShowMoreDialog] = useState(false);

  const handleNavigation = (path: string) => {
    navigate(path);
    setShowMoreDialog(false);
  };

  return (
    <>
      <Drawer
        variant="persistent"
        anchor="left"
        open={open}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
      >
        <DrawerHeader>
          <IconButton onClick={onToggle}>
            <ChevronLeftIcon />
          </IconButton>
        </DrawerHeader>
        <List>
          {mainMenuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton onClick={() => handleNavigation(item.path)}>
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
          <ListItem disablePadding>
            <ListItemButton onClick={() => setShowMoreDialog(true)}>
              <ListItemIcon><MoreIcon /></ListItemIcon>
              <ListItemText primary="More" />
            </ListItemButton>
          </ListItem>
        </List>
      </Drawer>

      <Dialog
        open={showMoreDialog}
        onClose={() => setShowMoreDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ textAlign: 'left' }}>All Applications</DialogTitle>
        <DialogContent>
          <List>
            {allMenuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton onClick={() => handleNavigation(item.path)}>
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default Sidebar; 