import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Paper,
  Select,
  SelectChangeEvent,
  TextField,
  Typography,
} from '@mui/material';
import React, { ReactNode, useState } from 'react';
import FilterBuilder from '../components/Filters/FilterBuilder';
import { Filter } from '../components/Filters/Filter';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const testFilters = [
  {
    id: '1',
    name: '16:9 aspect ratio',
    query:
      '{"id":"root","combinator":"and","rules":[{"id":"b06c8a69-747e-4e37-acb0-e8e9210e801e","field":"aspect_ratio_width","operator":"=","valueSource":"value","value":"16"},{"id":"d7360b89-0cac-4f23-bd2c-318778f08e09","field":"aspect_ratio_height","operator":"=","valueSource":"value","value":"9"}]}',
  },
  { id: '2', name: 'Holiday photos' },
  { id: '3', name: 'Wedding' },
];

const Filters = () => {
  const [filters, setFilters] = useState<Filter[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<Filter>();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState<boolean>(false);
  const [newFilterName, setNewFilterName] = useState('');

  // eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
  const handleFilterChange = (event: SelectChangeEvent<string>, child?: ReactNode) => {
    const filterId = event.target.value;
    const filter = filters.find((filter) => filter.id === filterId);
    if (filter) {
      setSelectedFilter(filter);
    }
  };

  const handleCreateNewFilter = () => {
    if (!newFilterName.trim()) return;

    const newFilter = {
      id: Date.now().toString(),
      name: newFilterName,
      query: '{"id":"root","combinator":"and","rules":[]}',
    } as Filter;

    setFilters([...filters, newFilter]);
    setNewFilterName('');
    setIsCreateDialogOpen(false);
    setSelectedFilter(newFilter);
  };

  const handleUpdateFilter = (id: string, name: string, rule: string) => {
    const updatedFilters = filters.map((filter) => (filter.id === id ? { ...filter, name, query: rule } : filter));
    setFilters(updatedFilters);
    const updatedFilter = updatedFilters.find((filter) => filter.id === id);
    setSelectedFilter(updatedFilter);
  };

  const handleDeleteFilter = (id: string) => {
    setFilters(filters.filter((f) => f.id !== id));
    if (selectedFilter?.id === id) {
      setSelectedFilter(undefined);
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Card>
          <CardHeader title="Gallery Filters" subheader="Create and manage custom filters for your Frame Gallery" />
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Select
                value={selectedFilter?.id || filters[0]?.id || ''}
                onChange={handleFilterChange}
                displayEmpty
                sx={{ minWidth: 300 }}
              >
                <MenuItem value="" disabled>
                  Select a filter...
                </MenuItem>
                {filters.map((filter) => (
                  <MenuItem key={filter.id} value={filter.id}>
                    {filter.name}
                  </MenuItem>
                ))}
              </Select>

              <IconButton color="primary" onClick={() => setIsCreateDialogOpen(true)} size="small">
                <AddIcon />
              </IconButton>

              {selectedFilter && (
                <>
                  <IconButton color="error" onClick={() => handleDeleteFilter(selectedFilter.id)} size="small">
                    <DeleteIcon />
                  </IconButton>
                </>
              )}
            </Box>
          </CardContent>
        </Card>

        {selectedFilter && (
          <Card>
            <CardHeader
              title={filters.find((f) => f.id === selectedFilter?.id)?.name}
              subheader="Define your filter conditions below"
            />
            <CardContent>
              <Paper
                variant="outlined"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '2px dashed rgba(0, 0, 0, 0.12)',
                }}
              >
                <FilterBuilder
                  selectedFilter={selectedFilter}
                  updateFilterHandler={handleUpdateFilter}
                />
              </Paper>
            </CardContent>
          </Card>
        )}

        <Dialog open={isCreateDialogOpen} onClose={() => setIsCreateDialogOpen(false)} maxWidth="xs" fullWidth>
          <DialogTitle>Create New Filter</DialogTitle>
          <DialogContent>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
              Give your new filter a name to get started
            </Typography>
            <TextField
              autoFocus
              fullWidth
              value={newFilterName}
              onChange={(e) => setNewFilterName(e.target.value)}
              placeholder="Filter name..."
              variant="outlined"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setIsCreateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateNewFilter} variant="contained">
              Create Filter
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </>
  );
};

export default Filters;
