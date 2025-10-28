import React, { useState } from 'react';
import {
  Container,
  Box,
  Typography,
  TextField,
  List,
  ListItem,
  ListItemText,
  Paper,
  Link,
  InputAdornment,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { useNavigate } from 'react-router-dom';

interface PicnicSpot {
  id: number;
  name: string;
  address: string;
  city: string;
  amenities: string[];
}

const picnicSpots: PicnicSpot[] = [
  {
    id: 1,
    name: 'Golden Gate Park Picnic Area',
    address: '501 Stanyan St, San Francisco, CA 94117',
    city: 'San Francisco',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Playground', 'Restrooms'],
  },
  {
    id: 2,
    name: 'Crissy Field',
    address: '1199 E Beach, San Francisco, CA 94129',
    city: 'San Francisco',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Beach Access', 'Restrooms'],
  },
  {
    id: 3,
    name: 'Lake Merritt Park',
    address: '666 Bellevue Ave, Oakland, CA 94610',
    city: 'Oakland',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Boat Rental', 'Playground'],
  },
  {
    id: 4,
    name: 'Tilden Park',
    address: '2501 Grizzly Peak Blvd, Orinda, CA 94563',
    city: 'Berkeley',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Botanical Garden', 'Hiking Trails'],
  },
  {
    id: 5,
    name: 'Shoreline Park',
    address: '3070 N Shoreline Blvd, Mountain View, CA 94043',
    city: 'Mountain View',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Lake Access', 'Bike Trails'],
  },
  {
    id: 6,
    name: 'Vasona Park',
    address: '333 Blossom Hill Rd, Los Gatos, CA 95032',
    city: 'Los Gatos',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Lake Access', 'Playground'],
  },
  {
    id: 7,
    name: 'Central Park',
    address: '909 Kiely Blvd, Santa Clara, CA 95051',
    city: 'Santa Clara',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Tennis Courts', 'Playground'],
  },
  {
    id: 8,
    name: 'Memorial Park',
    address: '800 E Santa Clara St, San Jose, CA 95112',
    city: 'San Jose',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Rose Garden', 'Playground'],
  },
  {
    id: 9,
    name: 'Coyote Point Park',
    address: '1701 Coyote Point Dr, San Mateo, CA 94401',
    city: 'San Mateo',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Beach Access', 'Playground'],
  },
  {
    id: 10,
    name: 'Huddart Park',
    address: '1100 Kings Mountain Rd, Woodside, CA 94062',
    city: 'Woodside',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Hiking Trails', 'Playground'],
  },
  {
    id: 11,
    name: 'Cuesta Park',
    address: '615 Cuesta St, Mountain View, CA 94040',
    city: 'Mountain View',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Tennis Courts', 'Playground'],
  },
  {
    id: 12,
    name: 'Rengstorff Park',
    address: '201 S Rengstorff Ave, Mountain View, CA 94040',
    city: 'Mountain View',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Pool', 'Playground'],
  },
  {
    id: 13,
    name: 'Mitchell Park',
    address: '600 E Meadow Dr, Palo Alto, CA 94303',
    city: 'Palo Alto',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Library', 'Playground'],
  },
  {
    id: 14,
    name: 'Baylands Park',
    address: '999 E Caribbean Dr, Sunnyvale, CA 94089',
    city: 'Sunnyvale',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Wetlands', 'Playground'],
  },
  {
    id: 15,
    name: 'Alum Rock Park',
    address: '15350 Penitencia Creek Rd, San Jose, CA 95127',
    city: 'San Jose',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Hiking Trails', 'Playground'],
  },
  {
    id: 16,
    name: 'Emma Prusch Farm Park',
    address: '647 S King Rd, San Jose, CA 95116',
    city: 'San Jose',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Farm Animals', 'Playground'],
  },
  {
    id: 17,
    name: 'Kelley Park',
    address: '1300 Senter Rd, San Jose, CA 95112',
    city: 'San Jose',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Japanese Garden', 'Playground'],
  },
  {
    id: 18,
    name: 'Sanborn Park',
    address: '16055 Sanborn Rd, Saratoga, CA 95070',
    city: 'Saratoga',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Hiking Trails', 'Playground'],
  },
  {
    id: 19,
    name: 'Villa Montalvo',
    address: '15400 Montalvo Rd, Saratoga, CA 95071',
    city: 'Saratoga',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Art Gallery', 'Gardens'],
  },
  {
    id: 20,
    name: 'Los Gatos Creek Park',
    address: '1250 Dell Ave, Campbell, CA 95008',
    city: 'Campbell',
    amenities: ['BBQ Grill', 'Outdoor Tables', 'Creek Access', 'Playground'],
  },
];

const PicnicSpots: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  const filteredSpots = picnicSpots.filter(
    (spot) =>
      spot.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      spot.city.toLowerCase().includes(searchTerm.toLowerCase()) ||
      spot.address.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSpotClick = (spotId: number) => {
    navigate(`/parks/picnic/reservation/${spotId}`);
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" gutterBottom>
          Picnic Spots in Bay Area
        </Typography>
        
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search by name, city, or address..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{ mb: 3 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />

        <Paper elevation={2}>
          <List>
            {filteredSpots.map((spot) => (
              <ListItem
                key={spot.id}
                divider
                sx={{
                  '&:hover': {
                    backgroundColor: 'action.hover',
                    cursor: 'pointer',
                  },
                }}
                onClick={() => handleSpotClick(spot.id)}
              >
                <ListItemText
                  primary={spot.name}
                  secondary={
                    <>
                      <Typography component="span" variant="body2" color="text.primary">
                        {spot.address}
                      </Typography>
                      <br />
                      <Typography component="span" variant="body2" color="text.secondary">
                        {spot.city}
                      </Typography>
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
        </Paper>
      </Box>
    </Container>
  );
};

export default PicnicSpots; 