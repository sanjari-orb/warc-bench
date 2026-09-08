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
  Grid,
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
  Assessment as AssessmentIcon,
  People as PeopleIcon,
  Description as DescriptionIcon,
  Warning as WarningIcon,
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  TrendingUp as TrendingUpIcon,
  CheckCircle as CheckCircleIcon,
  Pending as PendingIcon,
  Cancel as CancelIcon,
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
      id={`insurance-tabpanel-${index}`}
      aria-labelledby={`insurance-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const InsurancePage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedClaim, setSelectedClaim] = useState<number | null>(null);
  const [editingClaim, setEditingClaim] = useState<number | null>(null);
  const [selectedPolicy, setSelectedPolicy] = useState<number | null>(null);
  const [openNewPolicyDialog, setOpenNewPolicyDialog] = useState(false);
  const [newPolicy, setNewPolicy] = useState({
    policyNumber: '',
    clientName: '',
    type: '',
    status: 'Pending',
    premium: '',
    coverage: '',
    nextPayment: '',
  });
  const [editingPolicy, setEditingPolicy] = useState<number | null>(null);
  const [openSaveDialog, setOpenSaveDialog] = useState(false);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<{ id: number; type: 'claim' | 'policy' } | null>(null);
  const [itemToSave, setItemToSave] = useState<{ id: number; type: 'claim' | 'policy' } | null>(null);

  // Sample data for the dashboard
  const insuranceStats = [
    { title: 'Total Policies', value: '1,245', change: '+12', trend: 'up' },
    { title: 'Active Claims', value: '48', change: '-3', trend: 'down' },
    { title: 'Policy Renewals', value: '156', change: '+8', trend: 'up' },
    { title: 'Risk Score', value: '7.2', change: '-0.3', trend: 'up' },
  ];

  const recentPolicies = [
    {
      id: 1,
      policyNumber: 'POL-2024-001',
      clientName: 'John Smith',
      type: 'Life Insurance',
      status: 'Active',
      premium: '$450/mo',
      coverage: '$500K',
      nextPayment: '2024-05-15',
    },
    {
      id: 2,
      policyNumber: 'POL-2024-002',
      clientName: 'Sarah Johnson',
      type: 'Health Insurance',
      status: 'Pending',
      premium: '$320/mo',
      coverage: 'Family Plan',
      nextPayment: '2024-05-01',
    },
    {
      id: 3,
      policyNumber: 'POL-2024-003',
      clientName: 'Michael Brown',
      type: 'Auto Insurance',
      status: 'Active',
      premium: '$180/mo',
      coverage: 'Full Coverage',
      nextPayment: '2024-05-20',
    },
    {
      id: 4,
      policyNumber: 'POL-2024-004',
      clientName: 'Emily Davis',
      type: 'Home Insurance',
      status: 'Renewal',
      premium: '$250/mo',
      coverage: '$300K',
      nextPayment: '2024-06-01',
    },
  ];

  const [policies, setPolicies] = useState(recentPolicies);

  const activeClaims = [
    {
      id: 1,
      claimNumber: 'CLM-2024-001',
      policyNumber: 'POL-2024-001',
      clientName: 'John Smith',
      type: 'Life Insurance',
      status: 'In Review',
      amount: '$25,000',
      date: '2024-04-01',
      priority: 'High',
    },
    {
      id: 2,
      claimNumber: 'CLM-2024-002',
      policyNumber: 'POL-2024-003',
      clientName: 'Michael Brown',
      type: 'Auto Insurance',
      status: 'Pending Documents',
      amount: '$8,500',
      date: '2024-04-05',
      priority: 'Medium',
    },
    {
      id: 3,
      claimNumber: 'CLM-2024-003',
      policyNumber: 'POL-2024-004',
      clientName: 'Emily Davis',
      type: 'Home Insurance',
      status: 'Approved',
      amount: '$15,000',
      date: '2024-04-10',
      priority: 'Low',
    },
  ];

  const [claims, setClaims] = useState(activeClaims);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>, id: number, type: 'claim' | 'policy') => {
    setAnchorEl(event.currentTarget);
    if (type === 'claim') {
      setSelectedClaim(id);
    } else {
      setSelectedPolicy(id);
    }
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedClaim(null);
    setSelectedPolicy(null);
  };

  const handleNewPolicyClick = () => {
    setOpenNewPolicyDialog(true);
  };

  const handleNewPolicyClose = () => {
    setOpenNewPolicyDialog(false);
    setNewPolicy({
      policyNumber: '',
      clientName: '',
      type: '',
      status: 'Pending',
      premium: '',
      coverage: '',
      nextPayment: '',
    });
  };

  const handleNewPolicyTextChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setNewPolicy(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  const handleNewPolicySelectChange = (event: SelectChangeEvent) => {
    setNewPolicy(prev => ({
      ...prev,
      type: event.target.value
    }));
  };

  const handleNewPolicySubmit = () => {
    const newId = Math.max(...policies.map(p => p.id)) + 1;
    setPolicies(prev => [...prev, { ...newPolicy, id: newId }]);
    handleNewPolicyClose();
  };

  const handleDelete = (type: 'claim' | 'policy') => {
    if (type === 'claim') {
      setClaims(claims.filter(claim => claim.id !== selectedClaim));
    } else {
      setPolicies(policies.filter(policy => policy.id !== selectedPolicy));
    }
    handleMenuClose();
  };

  const handleStatusChange = (event: SelectChangeEvent, claimId: number) => {
    setClaims(claims.map(claim => 
      claim.id === claimId ? { ...claim, status: event.target.value } : claim
    ));
  };

  const handlePriorityChange = (event: SelectChangeEvent, claimId: number) => {
    setClaims(claims.map(claim => 
      claim.id === claimId ? { ...claim, priority: event.target.value } : claim
    ));
  };

  const handleAmountChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, claimId: number) => {
    setClaims(claims.map(claim => 
      claim.id === claimId ? { ...claim, amount: event.target.value } : claim
    ));
  };

  const handleDateChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, claimId: number) => {
    setClaims(claims.map(claim => 
      claim.id === claimId ? { ...claim, date: event.target.value } : claim
    ));
  };

  const handlePolicyStatusChange = (event: SelectChangeEvent, policyId: number) => {
    setPolicies(policies.map(policy => 
      policy.id === policyId ? { ...policy, status: event.target.value } : policy
    ));
  };

  const handlePolicyPremiumChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, policyId: number) => {
    setPolicies(policies.map(policy => 
      policy.id === policyId ? { ...policy, premium: event.target.value } : policy
    ));
  };

  const handlePolicyCoverageChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, policyId: number) => {
    setPolicies(policies.map(policy => 
      policy.id === policyId ? { ...policy, coverage: event.target.value } : policy
    ));
  };

  const handlePolicyNextPaymentChange = (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, policyId: number) => {
    setPolicies(policies.map(policy => 
      policy.id === policyId ? { ...policy, nextPayment: event.target.value } : policy
    ));
  };

  const riskMetrics = [
    { metric: 'Policy Lapse Rate', value: '2.4%', change: '-0.5%', trend: 'up' },
    { metric: 'Claims Approval Rate', value: '92%', change: '+2%', trend: 'up' },
    { metric: 'Customer Satisfaction', value: '4.8/5', change: '+0.2', trend: 'up' },
    { metric: 'Average Response Time', value: '24h', change: '-4h', trend: 'up' },
  ];

  const upcomingRenewals = [
    {
      id: 1,
      policyNumber: 'POL-2023-156',
      clientName: 'Robert Wilson',
      type: 'Life Insurance',
      renewalDate: '2024-05-15',
      premium: '$380/mo',
      status: 'Pending Review',
    },
    {
      id: 2,
      policyNumber: 'POL-2023-234',
      clientName: 'Lisa Anderson',
      type: 'Health Insurance',
      renewalDate: '2024-05-20',
      premium: '$420/mo',
      status: 'Approved',
    },
    {
      id: 3,
      policyNumber: 'POL-2023-345',
      clientName: 'David Miller',
      type: 'Auto Insurance',
      renewalDate: '2024-05-25',
      premium: '$160/mo',
      status: 'Pending Review',
    },
  ];

  const handleEditPolicy = (policyId: number) => {
    setEditingPolicy(policyId);
  };

  const handleEditClaim = (claimId: number) => {
    setEditingClaim(claimId);
  };

  const handleSaveClick = (id: number, type: 'claim' | 'policy') => {
    setItemToSave({ id, type });
    setOpenSaveDialog(true);
  };

  const handleDeleteClick = (id: number, type: 'claim' | 'policy') => {
    setItemToDelete({ id, type });
    setOpenDeleteDialog(true);
  };

  const handleSaveConfirm = () => {
    if (itemToSave) {
      if (itemToSave.type === 'claim') {
        setEditingClaim(null);
      } else {
        setEditingPolicy(null);
      }
      setOpenSaveDialog(false);
      setItemToSave(null);
    }
  };

  const handleSaveDiscard = () => {
    if (itemToSave) {
      if (itemToSave.type === 'claim') {
        setEditingClaim(null);
        setClaims(activeClaims);
      } else {
        setEditingPolicy(null);
        setPolicies(recentPolicies);
      }
      setOpenSaveDialog(false);
      setItemToSave(null);
    }
  };

  const handleDeleteConfirm = () => {
    if (itemToDelete) {
      if (itemToDelete.type === 'claim') {
        setClaims(claims.filter(claim => claim.id !== itemToDelete.id));
      } else {
        setPolicies(policies.filter(policy => policy.id !== itemToDelete.id));
      }
      setOpenDeleteDialog(false);
      setItemToDelete(null);
    }
  };

  const handleDeleteCancel = () => {
    setOpenDeleteDialog(false);
    setItemToDelete(null);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1">
          Insurance Dashboard
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={handleNewPolicyClick}
        >
          New Policy
        </Button>
      </Box>

      {/* Stats Overview */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 4 }}>
        {insuranceStats.map((stat, index) => (
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

      {/* New Policy Dialog */}
      <Dialog open={openNewPolicyDialog} onClose={handleNewPolicyClose} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Policy</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
            <TextField
              label="Policy Number"
              value={newPolicy.policyNumber}
              onChange={handleNewPolicyTextChange('policyNumber')}
              fullWidth
              required
            />
            <TextField
              label="Client Name"
              value={newPolicy.clientName}
              onChange={handleNewPolicyTextChange('clientName')}
              fullWidth
              required
            />
            <FormControl fullWidth required>
              <InputLabel>Type</InputLabel>
              <Select
                value={newPolicy.type}
                onChange={handleNewPolicySelectChange}
                label="Type"
              >
                <MenuItem value="Life Insurance">Life Insurance</MenuItem>
                <MenuItem value="Health Insurance">Health Insurance</MenuItem>
                <MenuItem value="Auto Insurance">Auto Insurance</MenuItem>
                <MenuItem value="Home Insurance">Home Insurance</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Premium"
              value={newPolicy.premium}
              onChange={handleNewPolicyTextChange('premium')}
              fullWidth
              required
            />
            <TextField
              label="Coverage"
              value={newPolicy.coverage}
              onChange={handleNewPolicyTextChange('coverage')}
              fullWidth
              required
            />
            <TextField
              label="Next Payment"
              type="date"
              value={newPolicy.nextPayment}
              onChange={handleNewPolicyTextChange('nextPayment')}
              fullWidth
              required
              InputLabelProps={{ shrink: true }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleNewPolicyClose}>Cancel</Button>
          <Button onClick={handleNewPolicySubmit} variant="contained" color="primary">
            Create Policy
          </Button>
        </DialogActions>
      </Dialog>

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
          <Typography>Are you sure you want to delete this {itemToDelete?.type}?</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>No</Button>
          <Button onClick={handleDeleteConfirm} variant="contained" color="error">
            Yes
          </Button>
        </DialogActions>
      </Dialog>

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
          <Tab icon={<DescriptionIcon />} label="Policies" />
          <Tab icon={<WarningIcon />} label="Claims" />
          <Tab icon={<AssessmentIcon />} label="Analytics" />
          <Tab icon={<PeopleIcon />} label="Clients" />
        </Tabs>

        <TabPanel value={tabValue} index={0}>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Policy Number</TableCell>
                  <TableCell>Client Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Premium</TableCell>
                  <TableCell>Coverage</TableCell>
                  <TableCell>Next Payment</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {policies.map((policy) => (
                  <TableRow key={policy.id}>
                    <TableCell>{policy.policyNumber}</TableCell>
                    <TableCell>{policy.clientName}</TableCell>
                    <TableCell>{policy.type}</TableCell>
                    <TableCell>
                      {editingPolicy === policy.id ? (
                        <FormControl size="small" fullWidth>
                          <Select
                            value={policy.status}
                            onChange={(e) => handlePolicyStatusChange(e, policy.id)}
                            displayEmpty
                          >
                            <MenuItem value="Active">Active</MenuItem>
                            <MenuItem value="Pending">Pending</MenuItem>
                            <MenuItem value="Renewal">Renewal</MenuItem>
                          </Select>
                        </FormControl>
                      ) : (
                        <Chip
                          label={policy.status}
                          color={
                            policy.status === 'Active'
                              ? 'success'
                              : policy.status === 'Pending'
                              ? 'warning'
                              : policy.status === 'Renewal'
                              ? 'info'
                              : 'default'
                          }
                          size="small"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      {editingPolicy === policy.id ? (
                        <TextField
                          size="small"
                          value={policy.premium}
                          onChange={(e) => handlePolicyPremiumChange(e, policy.id)}
                          fullWidth
                        />
                      ) : (
                        policy.premium
                      )}
                    </TableCell>
                    <TableCell>
                      {editingPolicy === policy.id ? (
                        <TextField
                          size="small"
                          value={policy.coverage}
                          onChange={(e) => handlePolicyCoverageChange(e, policy.id)}
                          fullWidth
                        />
                      ) : (
                        policy.coverage
                      )}
                    </TableCell>
                    <TableCell>
                      {editingPolicy === policy.id ? (
                        <TextField
                          size="small"
                          type="date"
                          value={policy.nextPayment}
                          onChange={(e) => handlePolicyNextPaymentChange(e, policy.id)}
                          fullWidth
                          InputLabelProps={{ shrink: true }}
                        />
                      ) : (
                        policy.nextPayment
                      )}
                    </TableCell>
                    <TableCell>
                      {editingPolicy === policy.id ? (
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleSaveClick(policy.id, 'policy')}
                          >
                            <SaveIcon />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteClick(policy.id, 'policy')}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Box>
                      ) : (
                        <IconButton
                          size="small"
                          onClick={(e) => handleMenuClick(e, policy.id, 'policy')}
                        >
                          <MoreVertIcon />
                        </IconButton>
                      )}
                      <Menu
                        anchorEl={anchorEl}
                        open={Boolean(anchorEl) && selectedPolicy === policy.id}
                        onClose={handleMenuClose}
                      >
                        <MenuItem onClick={() => handleEditPolicy(policy.id)}>
                          <EditIcon sx={{ mr: 1 }} /> Edit
                        </MenuItem>
                        <MenuItem onClick={() => handleDeleteClick(policy.id, 'policy')}>
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
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '2 2 66.666%' } }}>
              <Typography variant="h6" gutterBottom>
                Active Claims
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Claim Number</TableCell>
                      <TableCell>Client Name</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Amount</TableCell>
                      <TableCell>Date</TableCell>
                      <TableCell>Priority</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {claims.map((claim) => (
                      <TableRow key={claim.id}>
                        <TableCell>{claim.claimNumber}</TableCell>
                        <TableCell>{claim.clientName}</TableCell>
                        <TableCell>{claim.type}</TableCell>
                        <TableCell>
                          {editingClaim === claim.id ? (
                            <FormControl size="small" fullWidth>
                              <Select
                                value={claim.status}
                                onChange={(e) => handleStatusChange(e, claim.id)}
                                displayEmpty
                              >
                                <MenuItem value="In Review">In Review</MenuItem>
                                <MenuItem value="Pending Documents">Pending Documents</MenuItem>
                                <MenuItem value="Approved">Approved</MenuItem>
                              </Select>
                            </FormControl>
                          ) : (
                            <Chip
                              label={claim.status}
                              color={
                                claim.status === 'Approved'
                                  ? 'success'
                                  : claim.status === 'In Review'
                                  ? 'warning'
                                  : 'default'
                              }
                              size="small"
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          {editingClaim === claim.id ? (
                            <TextField
                              size="small"
                              value={claim.amount}
                              onChange={(e) => handleAmountChange(e, claim.id)}
                              fullWidth
                            />
                          ) : (
                            claim.amount
                          )}
                        </TableCell>
                        <TableCell>
                          {editingClaim === claim.id ? (
                            <TextField
                              size="small"
                              type="date"
                              value={claim.date}
                              onChange={(e) => handleDateChange(e, claim.id)}
                              fullWidth
                              InputLabelProps={{ shrink: true }}
                            />
                          ) : (
                            claim.date
                          )}
                        </TableCell>
                        <TableCell>
                          {editingClaim === claim.id ? (
                            <FormControl size="small" fullWidth>
                              <Select
                                value={claim.priority}
                                onChange={(e) => handlePriorityChange(e, claim.id)}
                                displayEmpty
                              >
                                <MenuItem value="High">High</MenuItem>
                                <MenuItem value="Medium">Medium</MenuItem>
                                <MenuItem value="Low">Low</MenuItem>
                              </Select>
                            </FormControl>
                          ) : (
                            <Chip
                              label={claim.priority}
                              color={
                                claim.priority === 'High'
                                  ? 'error'
                                  : claim.priority === 'Medium'
                                  ? 'warning'
                                  : 'success'
                              }
                              size="small"
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          {editingClaim === claim.id ? (
                            <Box sx={{ display: 'flex', gap: 1 }}>
                              <IconButton
                                size="small"
                                color="primary"
                                onClick={() => handleSaveClick(claim.id, 'claim')}
                              >
                                <SaveIcon />
                              </IconButton>
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleDeleteClick(claim.id, 'claim')}
                              >
                                <DeleteIcon />
                              </IconButton>
                            </Box>
                          ) : (
                            <IconButton
                              size="small"
                              onClick={(e) => handleMenuClick(e, claim.id, 'claim')}
                            >
                              <MoreVertIcon />
                            </IconButton>
                          )}
                          <Menu
                            anchorEl={anchorEl}
                            open={Boolean(anchorEl) && selectedClaim === claim.id}
                            onClose={handleMenuClose}
                          >
                            <MenuItem onClick={() => handleEditClaim(claim.id)}>
                              <EditIcon sx={{ mr: 1 }} /> Edit
                            </MenuItem>
                            <MenuItem onClick={() => handleDeleteClick(claim.id, 'claim')}>
                              <DeleteIcon sx={{ mr: 1 }} /> Delete
                            </MenuItem>
                          </Menu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '1 1 33.333%' } }}>
              <Typography variant="h6" gutterBottom>
                Risk Metrics
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
                    {riskMetrics.map((metric, index) => (
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
          <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3 }}>
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '2 2 66.666%' }, height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Typography color="text.secondary">Insurance Analytics Dashboard</Typography>
            </Paper>
            <Paper sx={{ p: 2, flex: { xs: '1 1 100%', md: '1 1 33.333%' } }}>
              <Typography variant="h6" gutterBottom>
                Upcoming Renewals
              </Typography>
              {upcomingRenewals.map((renewal) => (
                <Box key={renewal.id} sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="subtitle1">{renewal.clientName}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Policy: {renewal.policyNumber}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Type: {renewal.type}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Renewal Date: {renewal.renewalDate}
                  </Typography>
                  <Box sx={{ mt: 1 }}>
                    <Chip
                      label={renewal.status}
                      color={renewal.status === 'Approved' ? 'success' : 'warning'}
                      size="small"
                    />
                  </Box>
                </Box>
              ))}
            </Paper>
          </Box>
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            <Card sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Total Clients
                </Typography>
                <Typography variant="h4" color="primary">
                  1,245
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  +12% from last month
                </Typography>
              </CardContent>
            </Card>
            <Card sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Average Policy Value
                </Typography>
                <Typography variant="h4" color="primary">
                  $250K
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  +5% from last month
                </Typography>
              </CardContent>
            </Card>
            <Card sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Client Retention Rate
                </Typography>
                <Typography variant="h4" color="primary">
                  94%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  +2% from last month
                </Typography>
              </CardContent>
            </Card>
            <Card sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(25% - 18px)' } }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Average Response Time
                </Typography>
                <Typography variant="h4" color="primary">
                  24h
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  -4h from last month
                </Typography>
              </CardContent>
            </Card>
          </Box>
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default InsurancePage; 