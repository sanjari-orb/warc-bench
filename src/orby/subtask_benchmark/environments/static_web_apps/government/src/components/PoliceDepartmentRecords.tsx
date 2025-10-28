import React, { useState } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Link,
  Container,
  SelectChangeEvent,
} from '@mui/material';

interface PoliceRecord {
  caseNumber: string;
  dateUpdated: string;
  status: string;
  officerName: string;
  policeReport: string;
  videoLink: string;
}

const records: PoliceRecord[] = [
  {
    caseNumber: "PD-2024-0001",
    dateUpdated: "2024-06-01",
    status: "Open",
    officerName: "Jane Doe",
    policeReport: "https://example.com/reports/1",
    videoLink: "https://example.com/videos/1",
  },
  {
    caseNumber: "PD-2024-0002",
    dateUpdated: "2024-05-28",
    status: "Open",
    officerName: "John Smith",
    policeReport: "https://example.com/reports/2",
    videoLink: "https://example.com/videos/2",
  },
  {
    caseNumber: "PD-2024-0003",
    dateUpdated: "2024-05-25",
    status: "Under Investigation",
    officerName: "Emily Davis",
    policeReport: "https://example.com/reports/3",
    videoLink: "https://example.com/videos/3",
  },
  {
    caseNumber: "PD-2024-0004",
    dateUpdated: "2024-05-20",
    status: "Closed",
    officerName: "Michael Brown",
    policeReport: "https://example.com/reports/4",
    videoLink: "https://example.com/videos/4",
  },
  {
    caseNumber: "PD-2024-0005",
    dateUpdated: "2024-05-18",
    status: "Pending Review",
    officerName: "Sarah Johnson",
    policeReport: "https://example.com/reports/5",
    videoLink: "https://example.com/videos/5",
  },
  {
    caseNumber: "PD-2024-0006",
    dateUpdated: "2024-05-15",
    status: "Open",
    officerName: "Robert Wilson",
    policeReport: "https://example.com/reports/6",
    videoLink: "https://example.com/videos/6",
  },
  {
    caseNumber: "PD-2024-0007",
    dateUpdated: "2024-05-12",
    status: "Closed",
    officerName: "Jennifer Lee",
    policeReport: "https://example.com/reports/7",
    videoLink: "https://example.com/videos/7",
  },
  {
    caseNumber: "PD-2024-0008",
    dateUpdated: "2024-05-10",
    status: "Under Investigation",
    officerName: "David Miller",
    policeReport: "https://example.com/reports/8",
    videoLink: "https://example.com/videos/8",
  },
  {
    caseNumber: "PD-2024-0009",
    dateUpdated: "2024-05-08",
    status: "Pending Review",
    officerName: "Lisa Anderson",
    policeReport: "https://example.com/reports/9",
    videoLink: "https://example.com/videos/9",
  },
  {
    caseNumber: "PD-2024-0010",
    dateUpdated: "2024-05-05",
    status: "Closed",
    officerName: "James Clark",
    policeReport: "https://example.com/reports/10",
    videoLink: "https://example.com/videos/10",
  },
  {
    caseNumber: "PD-2024-0011",
    dateUpdated: "2024-05-03",
    status: "Open",
    officerName: "Patricia Moore",
    policeReport: "https://example.com/reports/11",
    videoLink: "https://example.com/videos/11",
  },
  {
    caseNumber: "PD-2024-0012",
    dateUpdated: "2024-05-01",
    status: "Closed",
    officerName: "Steven Hall",
    policeReport: "https://example.com/reports/12",
    videoLink: "https://example.com/videos/12",
  },
  {
    caseNumber: "PD-2024-0013",
    dateUpdated: "2024-04-28",
    status: "Under Investigation",
    officerName: "Karen Young",
    policeReport: "https://example.com/reports/13",
    videoLink: "https://example.com/videos/13",
  },
  {
    caseNumber: "PD-2024-0014",
    dateUpdated: "2024-04-25",
    status: "Pending Review",
    officerName: "Brian King",
    policeReport: "https://example.com/reports/14",
    videoLink: "https://example.com/videos/14",
  },
  {
    caseNumber: "PD-2024-0015",
    dateUpdated: "2024-04-22",
    status: "Closed",
    officerName: "Nancy Wright",
    policeReport: "https://example.com/reports/15",
    videoLink: "https://example.com/videos/15",
  },
  {
    caseNumber: "PD-2024-0016",
    dateUpdated: "2024-04-20",
    status: "Open",
    officerName: "Kevin Harris",
    policeReport: "https://example.com/reports/16",
    videoLink: "https://example.com/videos/16",
  },
  {
    caseNumber: "PD-2024-0017",
    dateUpdated: "2024-04-18",
    status: "Closed",
    officerName: "Laura Martin",
    policeReport: "https://example.com/reports/17",
    videoLink: "https://example.com/videos/17",
  },
  {
    caseNumber: "PD-2024-0018",
    dateUpdated: "2024-04-15",
    status: "Under Investigation",
    officerName: "Daniel Thompson",
    policeReport: "https://example.com/reports/18",
    videoLink: "https://example.com/videos/18",
  },
  {
    caseNumber: "PD-2024-0019",
    dateUpdated: "2024-04-12",
    status: "Pending Review",
    officerName: "Jessica White",
    policeReport: "https://example.com/reports/19",
    videoLink: "https://example.com/videos/19",
  },
  {
    caseNumber: "PD-2024-0020",
    dateUpdated: "2024-04-10",
    status: "Closed",
    officerName: "Matthew Garcia",
    policeReport: "https://example.com/reports/20",
    videoLink: "https://example.com/videos/20",
  },
  {
    caseNumber: "PD-2024-0021",
    dateUpdated: "2024-04-08",
    status: "Open",
    officerName: "Christopher Martinez",
    policeReport: "https://example.com/reports/21",
    videoLink: "https://example.com/videos/21",
  },
  {
    caseNumber: "PD-2024-0022",
    dateUpdated: "2024-04-05",
    status: "Under Investigation",
    officerName: "Amanda Taylor",
    policeReport: "https://example.com/reports/22",
    videoLink: "https://example.com/videos/22",
  },
  {
    caseNumber: "PD-2024-0023",
    dateUpdated: "2024-04-03",
    status: "Closed",
    officerName: "Richard Robinson",
    policeReport: "https://example.com/reports/23",
    videoLink: "https://example.com/videos/23",
  },
  {
    caseNumber: "PD-2024-0024",
    dateUpdated: "2024-04-01",
    status: "Pending Review",
    officerName: "Michelle Lewis",
    policeReport: "https://example.com/reports/24",
    videoLink: "https://example.com/videos/24",
  },
  {
    caseNumber: "PD-2024-0025",
    dateUpdated: "2024-03-29",
    status: "Open",
    officerName: "Thomas Walker",
    policeReport: "https://example.com/reports/25",
    videoLink: "https://example.com/videos/25",
  },
  {
    caseNumber: "PD-2024-0026",
    dateUpdated: "2024-03-27",
    status: "Closed",
    officerName: "Elizabeth Allen",
    policeReport: "https://example.com/reports/26",
    videoLink: "https://example.com/videos/26",
  },
  {
    caseNumber: "PD-2024-0027",
    dateUpdated: "2024-03-25",
    status: "Under Investigation",
    officerName: "Joseph Young",
    policeReport: "https://example.com/reports/27",
    videoLink: "https://example.com/videos/27",
  },
  {
    caseNumber: "PD-2024-0028",
    dateUpdated: "2024-03-22",
    status: "Pending Review",
    officerName: "Margaret Hernandez",
    policeReport: "https://example.com/reports/28",
    videoLink: "https://example.com/videos/28",
  },
  {
    caseNumber: "PD-2024-0029",
    dateUpdated: "2024-03-20",
    status: "Open",
    officerName: "Charles Nelson",
    policeReport: "https://example.com/reports/29",
    videoLink: "https://example.com/videos/29",
  },
  {
    caseNumber: "PD-2024-0030",
    dateUpdated: "2024-03-18",
    status: "Closed",
    officerName: "Susan Carter",
    policeReport: "https://example.com/reports/30",
    videoLink: "https://example.com/videos/30",
  },
  {
    caseNumber: "PD-2024-0031",
    dateUpdated: "2024-03-15",
    status: "Under Investigation",
    officerName: "Andrew Mitchell",
    policeReport: "https://example.com/reports/31",
    videoLink: "https://example.com/videos/31",
  },
  {
    caseNumber: "PD-2024-0032",
    dateUpdated: "2024-03-13",
    status: "Pending Review",
    officerName: "Rebecca Perez",
    policeReport: "https://example.com/reports/32",
    videoLink: "https://example.com/videos/32",
  },
  {
    caseNumber: "PD-2024-0033",
    dateUpdated: "2024-03-10",
    status: "Open",
    officerName: "George Roberts",
    policeReport: "https://example.com/reports/33",
    videoLink: "https://example.com/videos/33",
  },
  {
    caseNumber: "PD-2024-0034",
    dateUpdated: "2024-03-08",
    status: "Closed",
    officerName: "Linda Turner",
    policeReport: "https://example.com/reports/34",
    videoLink: "https://example.com/videos/34",
  },
  {
    caseNumber: "PD-2024-0035",
    dateUpdated: "2024-03-05",
    status: "Under Investigation",
    officerName: "Edward Phillips",
    policeReport: "https://example.com/reports/35",
    videoLink: "https://example.com/videos/35",
  },
  {
    caseNumber: "PD-2024-0036",
    dateUpdated: "2024-03-03",
    status: "Pending Review",
    officerName: "Barbara Campbell",
    policeReport: "https://example.com/reports/36",
    videoLink: "https://example.com/videos/36",
  },
  {
    caseNumber: "PD-2024-0037",
    dateUpdated: "2024-03-01",
    status: "Open",
    officerName: "William Parker",
    policeReport: "https://example.com/reports/37",
    videoLink: "https://example.com/videos/37",
  },
  {
    caseNumber: "PD-2024-0038",
    dateUpdated: "2024-02-28",
    status: "Closed",
    officerName: "Helen Evans",
    policeReport: "https://example.com/reports/38",
    videoLink: "https://example.com/videos/38",
  },
  {
    caseNumber: "PD-2024-0039",
    dateUpdated: "2024-02-25",
    status: "Under Investigation",
    officerName: "Frank Edwards",
    policeReport: "https://example.com/reports/39",
    videoLink: "https://example.com/videos/39",
  },
  {
    caseNumber: "PD-2024-0040",
    dateUpdated: "2024-02-22",
    status: "Pending Review",
    officerName: "Deborah Collins",
    policeReport: "https://example.com/reports/40",
    videoLink: "https://example.com/videos/40",
  },
  {
    caseNumber: "PD-2024-0041",
    dateUpdated: "2024-02-20",
    status: "Open",
    officerName: "Ronald Stewart",
    policeReport: "https://example.com/reports/41",
    videoLink: "https://example.com/videos/41",
  },
  {
    caseNumber: "PD-2024-0042",
    dateUpdated: "2024-02-18",
    status: "Closed",
    officerName: "Sharon Morris",
    policeReport: "https://example.com/reports/42",
    videoLink: "https://example.com/videos/42",
  },
  {
    caseNumber: "PD-2024-0043",
    dateUpdated: "2024-02-15",
    status: "Under Investigation",
    officerName: "Kenneth Rogers",
    policeReport: "https://example.com/reports/43",
    videoLink: "https://example.com/videos/43",
  },
  {
    caseNumber: "PD-2024-0044",
    dateUpdated: "2024-02-13",
    status: "Pending Review",
    officerName: "Carol Reed",
    policeReport: "https://example.com/reports/44",
    videoLink: "https://example.com/videos/44",
  },
  {
    caseNumber: "PD-2024-0045",
    dateUpdated: "2024-02-10",
    status: "Open",
    officerName: "Donald Cook",
    policeReport: "https://example.com/reports/45",
    videoLink: "https://example.com/videos/45",
  },
  {
    caseNumber: "PD-2024-0046",
    dateUpdated: "2024-02-08",
    status: "Closed",
    officerName: "Ruth Morgan",
    policeReport: "https://example.com/reports/46",
    videoLink: "https://example.com/videos/46",
  },
  {
    caseNumber: "PD-2024-0047",
    dateUpdated: "2024-02-05",
    status: "Under Investigation",
    officerName: "Gary Cooper",
    policeReport: "https://example.com/reports/47",
    videoLink: "https://example.com/videos/47",
  },
  {
    caseNumber: "PD-2024-0048",
    dateUpdated: "2024-02-03",
    status: "Pending Review",
    officerName: "Betty Richardson",
    policeReport: "https://example.com/reports/48",
    videoLink: "https://example.com/videos/48",
  },
  {
    caseNumber: "PD-2024-0049",
    dateUpdated: "2024-02-01",
    status: "Open",
    officerName: "Raymond Cox",
    policeReport: "https://example.com/reports/49",
    videoLink: "https://example.com/videos/49",
  },
  {
    caseNumber: "PD-2024-0050",
    dateUpdated: "2024-01-30",
    status: "Closed",
    officerName: "Virginia Howard",
    policeReport: "https://example.com/reports/50",
    videoLink: "https://example.com/videos/50",
  }
];

const PoliceDepartmentRecords: React.FC = () => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: SelectChangeEvent<number>) => {
    setRowsPerPage(Number(event.target.value));
    setPage(0);
  };

  const paginatedRecords = records.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  return (
    <Container maxWidth="lg">
      <Box py={4}>
        <Typography variant="h4" gutterBottom>
          Police Department Records
        </Typography>
        <Paper elevation={2} sx={{ width: '100%', mb: 2 }}>
          <TableContainer sx={{ maxHeight: rowsPerPage === 50 ? '70vh' : 'auto' }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>Case Number</TableCell>
                  <TableCell>Date Updated</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Officer Name</TableCell>
                  <TableCell>Police Report</TableCell>
                  <TableCell>Video Link</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedRecords.map((record) => (
                  <TableRow key={record.caseNumber}>
                    <TableCell>{record.caseNumber}</TableCell>
                    <TableCell>{record.dateUpdated}</TableCell>
                    <TableCell>
                      <Box
                        sx={{
                          display: 'inline-block',
                          px: 1,
                          py: 0.5,
                          borderRadius: 1,
                          backgroundColor:
                            record.status === 'Open'
                              ? '#ffebee'
                              : record.status === 'Closed'
                              ? '#e8f5e9'
                              : record.status === 'Under Investigation'
                              ? '#fff3e0'
                              : '#e3f2fd',
                          color:
                            record.status === 'Open'
                              ? '#c62828'
                              : record.status === 'Closed'
                              ? '#2e7d32'
                              : record.status === 'Under Investigation'
                              ? '#ef6c00'
                              : '#1565c0',
                        }}
                      >
                        {record.status}
                      </Box>
                    </TableCell>
                    <TableCell>{record.officerName}</TableCell>
                    <TableCell>
                      <Link href={record.policeReport} target="_blank" rel="noopener noreferrer">
                        View Report
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Link href={record.videoLink} target="_blank" rel="noopener noreferrer">
                        Watch Video
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <Box sx={{ display: 'flex', alignItems: 'center', p: 2 }}>
            <FormControl sx={{ m: 1, minWidth: 120 }}>
              <InputLabel>Rows per page</InputLabel>
              <Select
                value={rowsPerPage}
                onChange={handleChangeRowsPerPage}
                label="Rows per page"
              >
                <MenuItem value={10}>10</MenuItem>
                <MenuItem value={20}>20</MenuItem>
                <MenuItem value={50}>50</MenuItem>
              </Select>
            </FormControl>
            <TablePagination
              rowsPerPageOptions={[]}
              component="div"
              count={records.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
            />
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default PoliceDepartmentRecords; 