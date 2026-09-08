import React, { useState } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Button,
  Tabs,
  Tab,
  LinearProgress,
  Menu,
  MenuItem,
  TextField,
  Select,
  FormControl,
  InputLabel,
  SelectChangeEvent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  BarChart as BarChartIcon,
  TrendingUp as TrendingUpIcon,
  People as PeopleIcon,
  CalendarToday as CalendarIcon,
  Campaign as CampaignIcon,
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
} from '@mui/icons-material';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`marketing-tabpanel-${index}`}
      aria-labelledby={`marketing-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const MarketingPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedCampaign, setSelectedCampaign] = useState<number | null>(null);
  const [editingCampaign, setEditingCampaign] = useState<number | null>(null);
  const [openSaveDialog, setOpenSaveDialog] = useState(false);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [campaignToDelete, setCampaignToDelete] = useState<number | null>(null);
  const [openNewCampaignDialog, setOpenNewCampaignDialog] = useState(false);
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    status: 'Draft',
    reach: '',
    engagement: '',
    budget: '',
    roi: '',
  });

  // Sample data for the dashboard
  const campaignStats = [
    { title: 'Total Campaigns', value: '12', change: '+2', trend: 'up' },
    { title: 'Active Campaigns', value: '5', change: '+1', trend: 'up' },
    { title: 'Total Reach', value: '45.2K', change: '+12%', trend: 'up' },
    { title: 'Conversion Rate', value: '3.8%', change: '+0.5%', trend: 'up' },
  ];

  const keyMetrics = [
    { metric: 'Email Open Rate', value: '24.6%', change: '+2.5%', trend: 'up' },
    { metric: 'Click-through Rate', value: '41.2%', change: '+1.2%', trend: 'up' },
    { metric: 'Bounce Rate', value: '12%', change: '-1%', trend: 'down' },
    { metric: 'Cost per Lead', value: '$12.40', change: '-$1.2', trend: 'up' },
    { metric: 'Unsubscribe Rate', value: '0.8%', change: '-0.2%', trend: 'down' },
    { metric: 'Conversion Rate', value: '3.8%', change: '+0.5%', trend: 'up' },
  ];

  const recentCampaigns = [
    {
      id: 1,
      name: 'Summer Sale 2024',
      status: 'Active',
      reach: '12500',
      engagement: '4.2',
      budget: '5000',
      roi: '245',
    },
    {
      id: 2,
      name: 'Product Launch',
      status: 'Scheduled',
      reach: '0',
      engagement: '0',
      budget: '8000',
      roi: '0',
    },
    {
      id: 3,
      name: 'Customer Retention',
      status: 'Active',
      reach: '8200',
      engagement: '5.7',
      budget: '3500',
      roi: '180',
    },
    {
      id: 4,
      name: 'Re-engagement',
      status: 'Draft',
      reach: '0',
      engagement: '0',
      budget: '2000',
      roi: '0',
    },
  ];

  const [campaigns, setCampaigns] = useState(recentCampaigns);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const audienceSegments = [
    { name: 'High-Value Customers', count: 1243, growth: '+12%' },
    { name: 'New Leads', count: 3782, growth: '+8%' },
    { name: 'Inactive Users', count: 2157, growth: '-3%' },
    { name: 'Newsletter Subscribers', count: 8541, growth: '+15%' },
  ];

  const upcomingEvents = [
    {
      id: 1,
      title: 'Email Campaign Launch',
      date: 'Apr 15, 2024',
      type: 'Email',
      status: 'Scheduled',
    },
    {
      id: 2,
      title: 'Social Media Contest',
      date: 'Apr 18, 2024',
      type: 'Social',
      status: 'Planning',
    },
    {
      id: 3,
      title: 'Product Webinar',
      date: 'Apr 22, 2024',
      type: 'Webinar',
      status: 'Approved',
    },
  ];

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, id: number) => {
    setAnchorEl(event.currentTarget);
    setSelectedCampaign(id);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedCampaign(null);
  };

  const handleEditCampaign = (campaignId: number) => {
    setEditingCampaign(campaignId);
    handleMenuClose();
  };

  const handleSaveClick = (campaignId: number) => {
    setOpenSaveDialog(true);
  };

  const handleDeleteClick = (campaignId: number) => {
    setCampaignToDelete(campaignId);
    setOpenDeleteDialog(true);
  };

  const handleSaveConfirm = () => {
    setEditingCampaign(null);
    setOpenSaveDialog(false);
  };

  const handleSaveDiscard = () => {
    setEditingCampaign(null);
    setOpenSaveDialog(false);
    // Reset to original values
    setCampaigns(recentCampaigns);
  };

  const handleDeleteConfirm = () => {
    if (campaignToDelete) {
      setCampaigns(campaigns.filter(campaign => campaign.id !== campaignToDelete));
      setOpenDeleteDialog(false);
      setCampaignToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setOpenDeleteDialog(false);
    setCampaignToDelete(null);
  };

  const handleCampaignStatusChange = (event: SelectChangeEvent, campaignId: number) => {
    setCampaigns(campaigns.map(campaign => 
      campaign.id === campaignId ? { ...campaign, status: event.target.value } : campaign
    ));
  };

  const handleCampaignNameChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, campaignId: number) => {
    setCampaigns(campaigns.map(campaign => 
      campaign.id === campaignId ? { ...campaign, name: event.target.value } : campaign
    ));
  };

  const handleCampaignReachChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, campaignId: number) => {
    const value = event.target.value;
    // Only allow integers
    if (value === '' || /^\d+$/.test(value)) {
      setCampaigns(campaigns.map(campaign => 
        campaign.id === campaignId ? { ...campaign, reach: value } : campaign
      ));
    }
  };

  const handleCampaignEngagementChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, campaignId: number) => {
    const value = event.target.value;
    // Allow float values with up to 1 decimal place
    if (value === '' || /^\d*\.?\d{0,1}$/.test(value)) {
      setCampaigns(campaigns.map(campaign => 
        campaign.id === campaignId ? { ...campaign, engagement: value } : campaign
      ));
    }
  };

  const handleCampaignBudgetChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, campaignId: number) => {
    const value = event.target.value;
    // Allow float values with up to 2 decimal places
    if (value === '' || /^\d*\.?\d{0,2}$/.test(value)) {
      setCampaigns(campaigns.map(campaign => 
        campaign.id === campaignId ? { ...campaign, budget: value } : campaign
      ));
    }
  };

  const handleCampaignROIChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, campaignId: number) => {
    const value = event.target.value;
    // Allow float values with up to 1 decimal place
    if (value === '' || /^\d*\.?\d{0,1}$/.test(value)) {
      setCampaigns(campaigns.map(campaign => 
        campaign.id === campaignId ? { ...campaign, roi: value } : campaign
      ));
    }
  };

  // Helper function to format values for display
  const formatValue = (value: string, type: 'reach' | 'engagement' | 'budget' | 'roi') => {
    if (!value) return '';
    switch (type) {
      case 'reach':
        return value;
      case 'engagement':
        return `${value}%`;
      case 'budget':
        return `$${parseFloat(value).toLocaleString()}`;
      case 'roi':
        return `${value}%`;
      default:
        return value;
    }
  };

  // Helper function to clean values for editing
  const cleanValue = (value: string, type: 'reach' | 'engagement' | 'budget' | 'roi') => {
    if (!value) return '';
    switch (type) {
      case 'reach':
        return value.replace(/[^0-9]/g, '');
      case 'engagement':
        return value.replace(/[^0-9.]/g, '');
      case 'budget':
        return value.replace(/[^0-9.]/g, '');
      case 'roi':
        return value.replace(/[^0-9.]/g, '');
      default:
        return value;
    }
  };

  const handleNewCampaignClick = () => {
    setOpenNewCampaignDialog(true);
  };

  const handleNewCampaignClose = () => {
    setOpenNewCampaignDialog(false);
    setNewCampaign({
      name: '',
      status: 'Draft',
      reach: '',
      engagement: '',
      budget: '',
      roi: '',
    });
  };

  const handleNewCampaignTextChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setNewCampaign(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  const handleNewCampaignSelectChange = (event: SelectChangeEvent) => {
    setNewCampaign(prev => ({
      ...prev,
      status: event.target.value
    }));
  };

  const handleNewCampaignSubmit = () => {
    const newId = Math.max(...campaigns.map(c => c.id)) + 1;
    setCampaigns(prev => [...prev, { ...newCampaign, id: newId }]);
    handleNewCampaignClose();
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1">
          Marketing Dashboard
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={handleNewCampaignClick}
        >
          New Campaign
        </Button>
      </Box>

      {/* Stats Overview */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 4 }}>
        {campaignStats.map((stat, index) => (
          <Paper key={index} sx={{ p: 2, flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
            <Typography color="text.secondary" gutterBottom>
              {stat.title}
            </Typography>
            <Typography variant="h4" component="div">
              {stat.value}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
              <TrendingUpIcon
                sx={{
                  color: stat.trend === 'up' ? 'success.main' : 'error.main',
                  transform: stat.trend === 'down' ? 'rotate(180deg)' : 'none',
                }}
              />
              <Typography
                variant="body2"
                color={stat.trend === 'up' ? 'success.main' : 'error.main'}
                sx={{ ml: 1 }}
              >
                {stat.change}
              </Typography>
            </Box>
          </Paper>
        ))}
      </Box>

      {/* Main Content Tabs */}
      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<CampaignIcon />} label="Campaigns" />
          <Tab icon={<BarChartIcon />} label="Analytics" />
          <Tab icon={<PeopleIcon />} label="Audience" />
          <Tab icon={<CalendarIcon />} label="Calendar" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Campaign Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Reach</TableCell>
                  <TableCell>Engagement</TableCell>
                  <TableCell>Budget</TableCell>
                  <TableCell>ROI</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {campaigns.map((campaign) => (
                  <TableRow key={campaign.id}>
                    <TableCell>
                      {editingCampaign === campaign.id ? (
                        <TextField
                          size="small"
                          value={campaign.name}
                          onChange={(e) => handleCampaignNameChange(e, campaign.id)}
                          fullWidth
                        />
                      ) : (
                        campaign.name
                      )}
                    </TableCell>
                    <TableCell>
                      {editingCampaign === campaign.id ? (
                        <FormControl size="small" fullWidth>
                          <Select
                            value={campaign.status}
                            onChange={(e) => handleCampaignStatusChange(e, campaign.id)}
                            displayEmpty
                          >
                            <MenuItem value="Active">Active</MenuItem>
                            <MenuItem value="Scheduled">Scheduled</MenuItem>
                            <MenuItem value="Draft">Draft</MenuItem>
                          </Select>
                        </FormControl>
                      ) : (
                        <Chip
                          label={campaign.status}
                          color={
                            campaign.status === 'Active' 
                              ? 'success' 
                              : campaign.status === 'Scheduled'
                              ? 'warning'
                              : 'default'
                          }
                          size="small"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      {editingCampaign === campaign.id ? (
                        <TextField
                          size="small"
                          value={cleanValue(campaign.reach, 'reach')}
                          onChange={(e) => handleCampaignReachChange(e, campaign.id)}
                          fullWidth
                          type="number"
                          inputProps={{ 
                            min: 0,
                            step: 1,
                            pattern: '[0-9]*'
                          }}
                        />
                      ) : (
                        formatValue(campaign.reach, 'reach')
                      )}
                    </TableCell>
                    <TableCell>
                      {editingCampaign === campaign.id ? (
                        <TextField
                          size="small"
                          value={cleanValue(campaign.engagement, 'engagement')}
                          onChange={(e) => handleCampaignEngagementChange(e, campaign.id)}
                          fullWidth
                          type="number"
                          inputProps={{ 
                            min: 0,
                            max: 100,
                            step: 0.1,
                            pattern: '[0-9]*\.?[0-9]{0,1}'
                          }}
                        />
                      ) : (
                        formatValue(campaign.engagement, 'engagement')
                      )}
                    </TableCell>
                    <TableCell>
                      {editingCampaign === campaign.id ? (
                        <TextField
                          size="small"
                          value={cleanValue(campaign.budget, 'budget')}
                          onChange={(e) => handleCampaignBudgetChange(e, campaign.id)}
                          fullWidth
                          type="number"
                          inputProps={{ 
                            min: 0,
                            step: 100,
                            pattern: '[0-9]*\.?[0-9]{0,2}'
                          }}
                        />
                      ) : (
                        formatValue(campaign.budget, 'budget')
                      )}
                    </TableCell>
                    <TableCell>
                      {editingCampaign === campaign.id ? (
                        <TextField
                          size="small"
                          value={cleanValue(campaign.roi, 'roi')}
                          onChange={(e) => handleCampaignROIChange(e, campaign.id)}
                          fullWidth
                          type="number"
                          inputProps={{ 
                            min: 0,
                            step: 0.1,
                            pattern: '[0-9]*\.?[0-9]{0,1}'
                          }}
                        />
                      ) : (
                        formatValue(campaign.roi, 'roi')
                      )}
                    </TableCell>
                    <TableCell>
                      {editingCampaign === campaign.id ? (
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleSaveClick(campaign.id)}
                          >
                            <SaveIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteClick(campaign.id)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      ) : (
                        <IconButton
                          size="small"
                          onClick={(e) => handleMenuClick(e, campaign.id)}
                        >
                          <MoreVertIcon />
                        </IconButton>
                      )}
                      <Menu
                        anchorEl={anchorEl}
                        open={Boolean(anchorEl) && selectedCampaign === campaign.id}
                        onClose={handleMenuClose}
                      >
                        <MenuItem onClick={() => handleEditCampaign(campaign.id)}>
                          <EditIcon sx={{ mr: 1 }} /> Edit
                        </MenuItem>
                        <MenuItem onClick={() => handleDeleteClick(campaign.id)}>
                          <DeleteIcon sx={{ mr: 1 }} /> Delete
                        </MenuItem>
                      </Menu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '2 2 66.666%' }, height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography color="text.secondary">Campaign Performance Chart</Typography>
            </Paper>
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '1 1 33.333%' } }}>
              <Typography variant="h6" gutterBottom>
                Key Metrics
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Metric</TableCell>
                      <TableCell align="right">Value</TableCell>
                      <TableCell align="right">Change</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {keyMetrics.map((metric, index) => (
                      <TableRow key={index}>
                        <TableCell component="th" scope="row">
                          {metric.metric}
                        </TableCell>
                        <TableCell align="right">{metric.value}</TableCell>
                        <TableCell align="right">
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                            <TrendingUpIcon
                              sx={{
                                color: metric.trend === 'up' ? 'success.main' : 'error.main',
                                transform: metric.trend === 'down' ? 'rotate(180deg)' : 'none',
                                fontSize: '1rem',
                                mr: 0.5
                              }}
                            />
                            <Typography
                              variant="body2"
                              color={metric.trend === 'up' ? 'success.main' : 'error.main'}
                            >
                              {metric.change}
                            </Typography>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {audienceSegments.map((segment, index) => (
              <Card key={index} sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    {segment.name}
                  </Typography>
                  <Typography variant="h4" color="primary">
                    {segment.count.toLocaleString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Growth: {segment.growth}
                  </Typography>
                </CardContent>
              </Card>
            ))}
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '2 2 66.666%' }, height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography color="text.secondary">Marketing Calendar View</Typography>
            </Paper>
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '1 1 33.333%' } }}>
              <Typography variant="h6" gutterBottom>
                Upcoming Events
              </Typography>
              {upcomingEvents.map((event) => (
                <Box key={event.id} sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="subtitle1">{event.title}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {event.date}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Chip label={event.type} size="small" sx={{ mr: 1 }} />
                    <Chip label={event.status} size="small" color="primary" />
                  </Box>
                </Box>
              ))}
            </Paper>
          </Box>
        </TabPanel>
      </Paper>

      {/* Save Confirmation Dialog */}
      <Dialog open={openSaveDialog} onClose={() => setOpenSaveDialog(false)}>
        <DialogTitle>Save Changes</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to save the changes?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleSaveDiscard}>Discard</Button>
          <Button onClick={() => setOpenSaveDialog(false)}>Continue Editing</Button>
          <Button onClick={handleSaveConfirm} variant="contained" color="primary">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={openDeleteDialog} onClose={handleDeleteCancel}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>Are you sure you want to delete this campaign?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>No</Button>
          <Button onClick={handleDeleteConfirm} variant="contained" color="error">
            Yes
          </Button>
        </DialogActions>
      </Dialog>

      {/* New Campaign Dialog */}
      <Dialog open={openNewCampaignDialog} onClose={handleNewCampaignClose} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Campaign</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Campaign Name"
              value={newCampaign.name}
              onChange={handleNewCampaignTextChange('name')}
              fullWidth
              required
            />
            <FormControl fullWidth required>
              <InputLabel>Status</InputLabel>
              <Select
                value={newCampaign.status}
                onChange={handleNewCampaignSelectChange}
                label="Status"
              >
                <MenuItem value="Active">Active</MenuItem>
                <MenuItem value="Scheduled">Scheduled</MenuItem>
                <MenuItem value="Draft">Draft</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Reach"
              value={newCampaign.reach}
              onChange={handleNewCampaignTextChange('reach')}
              fullWidth
              required
              type="number"
              inputProps={{ 
                min: 0,
                step: 1,
                pattern: '[0-9]*'
              }}
            />
            <TextField
              label="Engagement (%)"
              value={newCampaign.engagement}
              onChange={handleNewCampaignTextChange('engagement')}
              fullWidth
              required
              type="number"
              inputProps={{ 
                min: 0,
                max: 100,
                step: 0.1,
                pattern: '[0-9]*\.?[0-9]{0,1}'
              }}
            />
            <TextField
              label="Budget ($)"
              value={newCampaign.budget}
              onChange={handleNewCampaignTextChange('budget')}
              fullWidth
              required
              type="number"
              inputProps={{ 
                min: 0,
                step: 100,
                pattern: '[0-9]*\.?[0-9]{0,2}'
              }}
            />
            <TextField
              label="ROI (%)"
              value={newCampaign.roi}
              onChange={handleNewCampaignTextChange('roi')}
              fullWidth
              required
              type="number"
              inputProps={{ 
                min: 0,
                step: 0.1,
                pattern: '[0-9]*\.?[0-9]{0,1}'
              }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleNewCampaignClose}>Cancel</Button>
          <Button onClick={handleNewCampaignSubmit} variant="contained" color="primary">
            Create Campaign
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default MarketingPage; 