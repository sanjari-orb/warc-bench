import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Container,
  IconButton,
  Checkbox,
  TextField,
  Box,
  TablePagination,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  InputAdornment,
  FormHelperText,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Search as SearchIcon,
  Add as AddIcon,
} from '@mui/icons-material';

interface Client {
  id: number;
  name: string;
  phoneNumber: string;
  address: string;
  pointOfContact: string;
}

interface PhoneNumberError {
  hasError: boolean;
  message: string;
}

const initialClients: Client[] = [
  {
    id: 1,
    name: 'Dunder Mifflin LLC',
    phoneNumber: '(555) 123-4567',
    address: '1725 Slough Avenue, Scranton, PA 18503',
    pointOfContact: 'Michael Scott',
  },
  {
    id: 2,
    name: 'Acme Corporation',
    phoneNumber: '(555) 234-5678',
    address: '123 Business Park, New York, NY 10001',
    pointOfContact: 'John Smith',
  },
  {
    id: 3,
    name: 'TechStart Solutions',
    phoneNumber: '(555) 345-6789',
    address: '456 Innovation Drive, San Francisco, CA 94105',
    pointOfContact: 'Sarah Johnson',
  },
  {
    id: 4,
    name: 'Global Industries Inc.',
    phoneNumber: '(555) 456-7890',
    address: '789 Corporate Plaza, Chicago, IL 60601',
    pointOfContact: 'Robert Wilson',
  },
  {
    id: 5,
    name: 'HealthCare Plus',
    phoneNumber: '(555) 567-8901',
    address: '321 Medical Center Blvd, Boston, MA 02114',
    pointOfContact: 'Dr. Emily Brown',
  },
  {
    id: 6,
    name: 'Green Energy Co.',
    phoneNumber: '(555) 678-9012',
    address: '654 Renewable Way, Seattle, WA 98101',
    pointOfContact: 'David Chen',
  },
  {
    id: 7,
    name: 'Creative Design Studio',
    phoneNumber: '(555) 789-0123',
    address: '987 Arts District, Los Angeles, CA 90012',
    pointOfContact: 'Lisa Anderson',
  },
  {
    id: 8,
    name: 'Financial Services Group',
    phoneNumber: '(555) 890-1234',
    address: '147 Wall Street, New York, NY 10005',
    pointOfContact: 'James Wilson',
  },
  {
    id: 9,
    name: 'Manufacturing Pro',
    phoneNumber: '(555) 901-2345',
    address: '258 Industrial Park, Detroit, MI 48226',
    pointOfContact: 'Thomas Miller',
  },
  {
    id: 10,
    name: 'Retail Solutions Inc.',
    phoneNumber: '(555) 012-3456',
    address: '369 Shopping Mall Blvd, Dallas, TX 75201',
    pointOfContact: 'Patricia Davis',
  },
];

const formatPhoneNumber = (value: string): string => {
  // Remove all non-digit characters
  const numbers = value.replace(/\D/g, '');
  
  // Format the phone number
  if (numbers.length <= 3) {
    return `(${numbers}`;
  } else if (numbers.length <= 6) {
    return `(${numbers.slice(0, 3)}) ${numbers.slice(3)}`;
  } else {
    return `(${numbers.slice(0, 3)}) ${numbers.slice(3, 6)}-${numbers.slice(6, 10)}`;
  }
};

const validatePhoneNumber = (value: string): PhoneNumberError => {
  // Remove all non-digit characters
  const numbers = value.replace(/\D/g, '');
  
  if (numbers.length > 10) {
    return {
      hasError: true,
      message: 'Exceeded maximum length'
    };
  }
  
  if (numbers.length < 10) {
    return {
      hasError: true,
      message: 'Phone number must be exactly 10 digits'
    };
  }
  
  if (/[a-zA-Z]/.test(value)) {
    return {
      hasError: true,
      message: 'Only numbers are allowed, alphabets are not allowed'
    };
  }
  
  return {
    hasError: false,
    message: ''
  };
};

const ClientsPage: React.FC = () => {
  const [clients, setClients] = useState<Client[]>(initialClients);
  const [selectedClients, setSelectedClients] = useState<number[]>([]);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [editingClient, setEditingClient] = useState<Client | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editForm, setEditForm] = useState<Partial<Client>>({});
  const [editPhoneError, setEditPhoneError] = useState<PhoneNumberError>({ hasError: false, message: '' });
  const [searchQuery, setSearchQuery] = useState('');
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [newClient, setNewClient] = useState<Partial<Client>>({
    name: '',
    phoneNumber: '',
    address: '',
    pointOfContact: '',
  });
  const [newPhoneError, setNewPhoneError] = useState<PhoneNumberError>({ hasError: false, message: '' });

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const newSelected = clients.map((client) => client.id);
      setSelectedClients(newSelected);
    } else {
      setSelectedClients([]);
    }
  };

  const handleSelectClient = (clientId: number) => {
    setSelectedClients((prev) =>
      prev.includes(clientId)
        ? prev.filter((id) => id !== clientId)
        : [...prev, clientId]
    );
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleEditClick = (client: Client) => {
    setEditingClient(client);
    setEditForm(client);
    setEditDialogOpen(true);
  };

  const handleEditSave = () => {
    if (editingClient && editForm) {
      setClients((prev) =>
        prev.map((client) =>
          client.id === editingClient.id ? { ...client, ...editForm } : client
        )
      );
      setEditDialogOpen(false);
      setEditingClient(null);
      setEditForm({});
    }
  };

  const handleEditCancel = () => {
    setEditDialogOpen(false);
    setEditingClient(null);
    setEditForm({});
  };

  const handleDelete = () => {
    setClients((prev) => prev.filter((client) => !selectedClients.includes(client.id)));
    setSelectedClients([]);
  };

  const handleDeleteSingle = (clientId: number) => {
    setClients((prev) => prev.filter((client) => client.id !== clientId));
  };

  const handleAddClick = () => {
    setAddDialogOpen(true);
  };

  const handleAddSave = () => {
    if (newClient.name && newClient.phoneNumber && newClient.address && newClient.pointOfContact) {
      const newId = Math.max(...clients.map(c => c.id)) + 1;
      const clientToAdd: Client = {
        id: newId,
        name: newClient.name,
        phoneNumber: newClient.phoneNumber,
        address: newClient.address,
        pointOfContact: newClient.pointOfContact,
      };
      setClients(prev => [clientToAdd, ...prev]);
      setAddDialogOpen(false);
      setNewClient({
        name: '',
        phoneNumber: '',
        address: '',
        pointOfContact: '',
      });
    }
  };

  const handleAddCancel = () => {
    setAddDialogOpen(false);
    setNewClient({
      name: '',
      phoneNumber: '',
      address: '',
      pointOfContact: '',
    });
  };

  const handleEditPhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formattedValue = formatPhoneNumber(e.target.value);
    const error = validatePhoneNumber(e.target.value);
    setEditPhoneError(error);
    setEditForm({ ...editForm, phoneNumber: formattedValue });
  };

  const handleNewPhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formattedValue = formatPhoneNumber(e.target.value);
    const error = validatePhoneNumber(e.target.value);
    setNewPhoneError(error);
    setNewClient({ ...newClient, phoneNumber: formattedValue });
  };

  const filteredClients = clients.filter((client) =>
    Object.values(client).some((value) =>
      value.toString().toLowerCase().includes(searchQuery.toLowerCase())
    )
  );

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Client List
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={handleAddClick}
        >
          Add New Client
        </Button>
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Checkbox
            checked={selectedClients.length === clients.length}
            indeterminate={selectedClients.length > 0 && selectedClients.length < clients.length}
            onChange={handleSelectAll}
          />
          <Typography component="span">
            Select All
          </Typography>
        </Box>
        {selectedClients.length > 0 && (
          <Box>
            <Button
              variant="contained"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleDelete}
              sx={{ mr: 1 }}
            >
              Delete Selected
            </Button>
          </Box>
        )}
      </Box>
      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search clients..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={selectedClients.length === clients.length}
                  indeterminate={selectedClients.length > 0 && selectedClients.length < clients.length}
                  onChange={handleSelectAll}
                />
              </TableCell>
              <TableCell>Business Name</TableCell>
              <TableCell>Phone Number</TableCell>
              <TableCell>Address</TableCell>
              <TableCell>Point of Contact</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredClients
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((client) => (
                <TableRow key={client.id}>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedClients.includes(client.id)}
                      onChange={() => handleSelectClient(client.id)}
                    />
                  </TableCell>
                  <TableCell>{client.name}</TableCell>
                  <TableCell>{client.phoneNumber}</TableCell>
                  <TableCell>{client.address}</TableCell>
                  <TableCell>{client.pointOfContact}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton
                        size="small"
                        onClick={() => handleEditClick(client)}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteSingle(client.id)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={filteredClients.length}
        page={page}
        onPageChange={handleChangePage}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={handleChangeRowsPerPage}
        rowsPerPageOptions={[5, 10, 25]}
      />

      <Dialog open={editDialogOpen} onClose={handleEditCancel}>
        <DialogTitle>Edit Client Information</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <TextField
              fullWidth
              label="Phone Number"
              value={editForm.phoneNumber || ''}
              onChange={handleEditPhoneChange}
              error={editPhoneError.hasError}
              helperText={editPhoneError.message}
              sx={{ mb: 2 }}
              placeholder="(   )   -    "
            />
            <TextField
              fullWidth
              label="Address"
              value={editForm.address || ''}
              onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
              multiline
              rows={3}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleEditCancel}>Cancel</Button>
          <Button 
            onClick={handleEditSave} 
            variant="contained" 
            color="primary"
            disabled={editPhoneError.hasError}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={addDialogOpen} onClose={handleAddCancel} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Client</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              label="Business Name"
              value={newClient.name}
              onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
              required
            />
            <TextField
              fullWidth
              label="Phone Number"
              value={newClient.phoneNumber}
              onChange={handleNewPhoneChange}
              error={newPhoneError.hasError}
              helperText={newPhoneError.message}
              required
              placeholder="(   )   -    "
            />
            <TextField
              fullWidth
              label="Address"
              value={newClient.address}
              onChange={(e) => setNewClient({ ...newClient, address: e.target.value })}
              multiline
              rows={3}
              required
            />
            <TextField
              fullWidth
              label="Point of Contact"
              value={newClient.pointOfContact}
              onChange={(e) => setNewClient({ ...newClient, pointOfContact: e.target.value })}
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleAddCancel}>Cancel</Button>
          <Button 
            onClick={handleAddSave} 
            variant="contained" 
            color="primary"
            disabled={!newClient.name || !newClient.phoneNumber || !newClient.address || !newClient.pointOfContact || newPhoneError.hasError}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default ClientsPage; 