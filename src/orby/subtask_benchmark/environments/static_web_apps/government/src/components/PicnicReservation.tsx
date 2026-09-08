import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  Typography,
  Paper,
  Chip,
  Grid,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';

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

interface TimeSlot {
  start: string;
  end: string;
  available: boolean;
}

// Add a simple seeded PRNG (mulberry32)
function mulberry32(seed: number) {
  return function() {
    let t = seed += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
}

// Deterministically generate time slots for a given date string
function generateSeededTimeSlots(dateStr: string): TimeSlot[] {
  // Use the date string to create a numeric seed
  let seed = 0;
  for (let i = 0; i < dateStr.length; i++) {
    seed += dateStr.charCodeAt(i) * (i + 1);
  }
  const rand = mulberry32(seed);

  const slots: TimeSlot[] = [];
  for (let hour = 8; hour <= 20; hour++) {
    slots.push({
      start: `${hour.toString().padStart(2, '0')}:00`,
      end: `${hour.toString().padStart(2, '0')}:30`,
      available: rand() > 0.3, // 70% chance of being available
    });
    slots.push({
      start: `${hour.toString().padStart(2, '0')}:30`,
      end: `${(hour + 1).toString().padStart(2, '0')}:00`,
      available: rand() > 0.3,
    });
  }
  return slots;
}

const PicnicReservation: React.FC = () => {
  const { spotId } = useParams<{ spotId: string }>();
  const navigate = useNavigate();
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedSlots, setSelectedSlots] = useState<TimeSlot[]>([]);
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([]);
  const [totalCost, setTotalCost] = useState(0);

  const spot = picnicSpots.find((s) => s.id === Number(spotId));

  useEffect(() => {
    if (selectedDate) {
      const dateStr = selectedDate.toISOString().split('T')[0];
      setTimeSlots(generateSeededTimeSlots(dateStr));
    } else {
      setTimeSlots([]);
    }
  }, [selectedDate]);

  useEffect(() => {
    const cost = selectedSlots.length * 25; // $25 per half hour
    setTotalCost(cost);
  }, [selectedSlots]);

  const handleSlotClick = (slot: TimeSlot) => {
    if (!slot.available) return;

    const slotIndex = selectedSlots.findIndex(
      (s) => s.start === slot.start && s.end === slot.end
    );

    if (slotIndex === -1) {
      // Check if we can add this slot (must be consecutive)
      if (selectedSlots.length === 0) {
        setSelectedSlots([slot]);
      } else {
        const lastSlot = selectedSlots[selectedSlots.length - 1];
        if (lastSlot.end === slot.start) {
          if (selectedSlots.length < 6) { // Maximum 3 hours (6 half-hour slots)
            setSelectedSlots([...selectedSlots, slot]);
          }
        }
      }
    } else {
      // Remove the slot and all slots after it
      setSelectedSlots(selectedSlots.slice(0, slotIndex));
    }
  };

  const handleReserve = () => {
    navigate('/parks/picnic/payment', {
      state: {
        spotId: spot?.id,
        spotName: spot?.name,
        selectedDate: selectedDate,
        selectedSlots: selectedSlots,
        totalCost: totalCost
      }
    });
  };

  if (!spot) {
    return (
      <Container>
        <Typography variant="h5">Spot not found</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="md">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" gutterBottom>
          {spot.name}
        </Typography>
        <Typography variant="subtitle1" gutterBottom>
          {spot.address}
        </Typography>

        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Amenities
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {spot.amenities.map((amenity) => (
              <Chip key={amenity} label={amenity} color="primary" variant="outlined" />
            ))}
          </Box>
        </Paper>

        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Select Date and Time
          </Typography>

          <TextField
            type="date"
            label="Select Date"
            value={selectedDate ? selectedDate.toISOString().split('T')[0] : ''}
            onChange={(e) => {
              const date = e.target.value ? new Date(e.target.value) : null;
              setSelectedDate(date);
              setSelectedSlots([]);
            }}
            fullWidth
            sx={{ mb: 2 }}
            InputLabelProps={{
              shrink: true,
            }}
          />

          {selectedDate && (
            <>
              <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                Available Time Slots
              </Typography>
              <Grid container spacing={1}>
                {timeSlots.map((slot) => (
                  <Grid item xs={6} sm={4} md={3} key={`${slot.start}-${slot.end}`}>
                    <Button
                      variant={
                        selectedSlots.some(
                          (s) => s.start === slot.start && s.end === slot.end
                        )
                          ? 'contained'
                          : 'outlined'
                      }
                      color={slot.available ? 'primary' : 'error'}
                      disabled={!slot.available}
                      onClick={() => handleSlotClick(slot)}
                      fullWidth
                      sx={{ mb: 1 }}
                    >
                      {slot.start} - {slot.end}
                    </Button>
                  </Grid>
                ))}
              </Grid>

              {selectedSlots.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    Selected Time Slots
                  </Typography>
                  <Typography variant="body1" gutterBottom>
                    {selectedSlots.map((slot) => `${slot.start} - ${slot.end}`).join(', ')}
                  </Typography>
                  <Typography variant="h6" sx={{ mt: 2 }}>
                    Total Cost: ${totalCost}
                  </Typography>
                  <Box sx={{ mt: 2 }}>
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={handleReserve}
                      fullWidth
                    >
                      Reserve and Pay Now
                    </Button>
                  </Box>
                </Box>
              )}
            </>
          )}
        </Paper>
      </Box>
    </Container>
  );
};

export default PicnicReservation; 