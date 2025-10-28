import React from 'react';
import {
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Box,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
} from '@mui/material';
import {
  DirectionsWalk,
  Terrain,
  AccessTime,
  LocationOn,
  Park,
  DirectionsBike,
  Pets,
  SportsSoccer,
  Pool,
  Restaurant,
} from '@mui/icons-material';

interface Trail {
  name: string;
  distance: string;
  elevationGain: string;
  difficulty: 'Easy' | 'Moderate' | 'Hard';
}

interface Park {
  name: string;
  image: string;
  address: string;
  hours: string;
  description: string;
  amenities: string[];
  trails: Trail[];
}

const parks: Park[] = [
  {
    name: "Sunset Ridge Park",
    image: "https://source.unsplash.com/random/800x600/?park",
    address: "1234 Mountain View Drive",
    hours: "6:00 AM - 10:00 PM",
    description: "A scenic park offering breathtaking views of the city skyline and surrounding mountains. Perfect for family outings and nature enthusiasts.",
    amenities: ["Picnic Areas", "Playground", "Restrooms", "BBQ Grills", "Dog Park"],
    trails: [
      { name: "Sunset Loop", distance: "2.5 miles", elevationGain: "300 ft", difficulty: "Easy" },
      { name: "Ridge Trail", distance: "4.2 miles", elevationGain: "800 ft", difficulty: "Moderate" },
    ],
  },
  {
    name: "Green Valley Park",
    image: "https://source.unsplash.com/random/800x600/?forest",
    address: "5678 Valley Road",
    hours: "5:00 AM - 11:00 PM",
    description: "A lush green space with diverse flora and fauna. Features a beautiful lake and multiple recreational areas.",
    amenities: ["Fishing Lake", "Boat Rentals", "Tennis Courts", "Basketball Courts", "Visitor Center"],
    trails: [
      { name: "Lake Loop", distance: "1.8 miles", elevationGain: "50 ft", difficulty: "Easy" },
      { name: "Valley View", distance: "3.5 miles", elevationGain: "600 ft", difficulty: "Moderate" },
    ],
  },
  {
    name: "Oakwood Heights",
    image: "https://source.unsplash.com/random/800x600/?oak",
    address: "9012 Oak Street",
    hours: "7:00 AM - 9:00 PM",
    description: "Historic park known for its ancient oak trees and well-maintained gardens. A peaceful retreat in the heart of the city.",
    amenities: ["Botanical Garden", "Amphitheater", "Café", "Art Gallery", "Walking Paths"],
    trails: [
      { name: "Oak Trail", distance: "1.2 miles", elevationGain: "100 ft", difficulty: "Easy" },
      { name: "Garden Path", distance: "0.8 miles", elevationGain: "20 ft", difficulty: "Easy" },
    ],
  },
  {
    name: "Crystal Lake Park",
    image: "https://source.unsplash.com/random/800x600/?lake",
    address: "3456 Lakeview Avenue",
    hours: "6:00 AM - 10:00 PM",
    description: "A popular destination for water activities and nature walks. The crystal-clear lake is perfect for swimming and kayaking.",
    amenities: ["Swimming Area", "Kayak Rentals", "Camping Sites", "Fishing Pier", "Snack Bar"],
    trails: [
      { name: "Lakeside Trail", distance: "2.0 miles", elevationGain: "150 ft", difficulty: "Easy" },
      { name: "Forest Loop", distance: "3.8 miles", elevationGain: "450 ft", difficulty: "Moderate" },
    ],
  },
  {
    name: "Mountain View Preserve",
    image: "https://source.unsplash.com/random/800x600/?mountain",
    address: "7890 Summit Road",
    hours: "5:00 AM - 8:00 PM",
    description: "A challenging park for experienced hikers with stunning mountain views and diverse wildlife.",
    amenities: ["Observation Deck", "Visitor Center", "Rest Areas", "Emergency Phone", "Water Stations"],
    trails: [
      { name: "Summit Trail", distance: "5.5 miles", elevationGain: "1200 ft", difficulty: "Hard" },
      { name: "Eagle's Nest", distance: "3.2 miles", elevationGain: "900 ft", difficulty: "Moderate" },
    ],
  },
  {
    name: "Riverside Park",
    image: "https://source.unsplash.com/random/800x600/?river",
    address: "2345 River Road",
    hours: "6:00 AM - 10:00 PM",
    description: "A beautiful park along the river with multiple recreational facilities and scenic views.",
    amenities: ["Boat Launch", "Fishing Spots", "Picnic Shelters", "Bike Path", "Playground"],
    trails: [
      { name: "River Walk", distance: "2.8 miles", elevationGain: "100 ft", difficulty: "Easy" },
      { name: "Riverside Loop", distance: "4.0 miles", elevationGain: "200 ft", difficulty: "Moderate" },
    ],
  },
  {
    name: "Wildflower Meadows",
    image: "https://source.unsplash.com/random/800x600/?meadow",
    address: "6789 Meadow Lane",
    hours: "7:00 AM - 9:00 PM",
    description: "A peaceful park known for its seasonal wildflowers and butterfly garden. Perfect for nature photography.",
    amenities: ["Butterfly Garden", "Photography Spots", "Nature Center", "Walking Paths", "Rest Areas"],
    trails: [
      { name: "Wildflower Trail", distance: "1.5 miles", elevationGain: "50 ft", difficulty: "Easy" },
      { name: "Meadow Loop", distance: "2.2 miles", elevationGain: "100 ft", difficulty: "Easy" },
    ],
  },
  {
    name: "Pine Forest Park",
    image: "https://source.unsplash.com/random/800x600/?pine",
    address: "1234 Forest Drive",
    hours: "6:00 AM - 10:00 PM",
    description: "A dense pine forest offering shaded trails and a cool retreat during summer months.",
    amenities: ["Camping Area", "BBQ Pits", "Horseback Riding", "Mountain Biking", "Restrooms"],
    trails: [
      { name: "Pine Trail", distance: "3.0 miles", elevationGain: "400 ft", difficulty: "Moderate" },
      { name: "Forest Loop", distance: "4.5 miles", elevationGain: "600 ft", difficulty: "Moderate" },
    ],
  },
  {
    name: "Heritage Park",
    image: "https://source.unsplash.com/random/800x600/?historic",
    address: "5678 Heritage Lane",
    hours: "8:00 AM - 8:00 PM",
    description: "A historic park featuring restored buildings and educational exhibits about the city's past.",
    amenities: ["Historic Buildings", "Museum", "Guided Tours", "Gift Shop", "Café"],
    trails: [
      { name: "History Walk", distance: "1.0 mile", elevationGain: "30 ft", difficulty: "Easy" },
      { name: "Heritage Loop", distance: "1.8 miles", elevationGain: "50 ft", difficulty: "Easy" },
    ],
  },
  {
    name: "Canyon View Park",
    image: "https://source.unsplash.com/random/800x600/?canyon",
    address: "9012 Canyon Road",
    hours: "5:00 AM - 9:00 PM",
    description: "A dramatic park featuring stunning canyon views and challenging hiking trails.",
    amenities: ["Viewing Platforms", "Rock Climbing", "Visitor Center", "Rest Areas", "Water Stations"],
    trails: [
      { name: "Canyon Rim", distance: "4.0 miles", elevationGain: "800 ft", difficulty: "Moderate" },
      { name: "Canyon Floor", distance: "5.5 miles", elevationGain: "1000 ft", difficulty: "Hard" },
    ],
  },
];

const ParksAndTrails: React.FC = () => {
  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h3" component="h1" gutterBottom align="center">
        Parks & Trails
      </Typography>
      <Typography variant="subtitle1" gutterBottom align="center" color="text.secondary">
        Discover the natural beauty of our city's parks and trails
      </Typography>
      
      <Grid container spacing={4} sx={{ mt: 2 }}>
        {parks.map((park) => (
          <Grid item xs={12} key={park.name}>
            <Card sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' } }}>
              <CardMedia
                component="img"
                sx={{ width: { xs: '100%', md: 300 }, height: 200 }}
                image={park.image}
                alt={park.name}
              />
              <CardContent sx={{ flex: 1 }}>
                <Typography variant="h5" component="h2" gutterBottom>
                  {park.name}
                </Typography>
                
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <LocationOn color="action" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    {park.address}
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AccessTime color="action" sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    {park.hours}
                  </Typography>
                </Box>
                
                <Typography variant="body1" paragraph>
                  {park.description}
                </Typography>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Amenities:
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {park.amenities.map((amenity) => (
                      <Chip
                        key={amenity}
                        label={amenity}
                        size="small"
                        icon={
                          amenity.includes('Park') ? <Pets /> :
                          amenity.includes('Court') ? <SportsSoccer /> :
                          amenity.includes('Pool') ? <Pool /> :
                          amenity.includes('Café') ? <Restaurant /> :
                          <Park />
                        }
                      />
                    ))}
                  </Box>
                </Box>
                
                <Divider sx={{ my: 2 }} />
                
                <Typography variant="subtitle2" gutterBottom>
                  Trails:
                </Typography>
                <List dense>
                  {park.trails.map((trail) => (
                    <ListItem key={trail.name}>
                      <ListItemIcon>
                        {trail.difficulty === 'Easy' ? <DirectionsWalk /> :
                         trail.difficulty === 'Moderate' ? <DirectionsBike /> :
                         <Terrain />}
                      </ListItemIcon>
                      <ListItemText
                        primary={trail.name}
                        secondary={
                          <>
                            <Typography component="span" variant="body2" color="text.primary">
                              Distance: {trail.distance} • Elevation Gain: {trail.elevationGain}
                            </Typography>
                            <br />
                            <Typography component="span" variant="body2" color="text.secondary">
                              Difficulty: {trail.difficulty}
                            </Typography>
                          </>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default ParksAndTrails; 