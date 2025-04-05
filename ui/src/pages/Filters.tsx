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
  Select,
  SelectChangeEvent,
  TextField,
  Typography,
} from '@mui/material';
import React, { ReactNode, useState, useEffect } from 'react';
import FilterBuilder from '../components/Filters/FilterBuilder';
import { Filter } from '../components/Filters/Filter';
import { Add as AddIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { filterService } from '../services/filterService';

const Filters = () => {
  const [filters, setFilters] = useState<Filter[]>([]);
  const [selectedFilter, setSelectedFilter] = useState<Filter>();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState<boolean>(false);
  const [newFilterName, setNewFilterName] = useState('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadFilters();
  }, []);

  const loadFilters = async () => {
    try {
      const fetchedFilters = await filterService.getFilters();
      setFilters(fetchedFilters);
    } catch (err) {
      setError('Failed to load filters');
      console.error(err);
    }
  };

  const handleFilterChange = (event: SelectChangeEvent<number>, child?: ReactNode) => {
    const filterId = event.target.value;
    const filter = filters.find((filter) => filter.id === filterId);
    if (filter) {
      setSelectedFilter(filter);
    }
  };

  const handleCreateNewFilter = async () => {
    if (!newFilterName.trim()) return;

    try {
      const newFilter = await filterService.createFilter({
        name: newFilterName,
        query: '{"id":"root","combinator":"and","rules":[]}',
      });

      setFilters([...filters, newFilter]);
      setNewFilterName('');
      setIsCreateDialogOpen(false);
      setSelectedFilter(newFilter);
    } catch (err) {
      setError('Failed to create filter');
      console.error(err);
    }
  };

  const handleUpdateFilter = async (id: number, name: string, query: string) => {
    try {
      const updatedFilter = await filterService.updateFilter(id, { name, query });
      const updatedFilters = filters.map((filter) => (filter.id === id ? updatedFilter : filter));
      setFilters(updatedFilters);
      setSelectedFilter(updatedFilter);
    } catch (err) {
      setError('Failed to update filter');
      console.error(err);
    }
  };

  const handleDeleteFilter = async (id: number) => {
    try {
      await filterService.deleteFilter(id);
      setFilters(filters.filter((f) => f.id !== id));
      if (selectedFilter?.id === id) {
        setSelectedFilter(undefined);
      }
    } catch (err) {
      setError('Failed to delete filter');
      console.error(err);
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Card>
          <CardHeader title="Gallery Filters" subheader="Create and manage custom filters for your Frame Gallery" />
          <CardContent>
            {error && (
              <Typography color="error" sx={{ mb: 2 }}>
                {error}
              </Typography>
            )}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Select
                value={selectedFilter?.id ?? ''}
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
              <IconButton color="primary" onClick={() => setIsCreateDialogOpen(true)}>
                <AddIcon />
              </IconButton>
              {selectedFilter && (
                <IconButton color="error" onClick={() => handleDeleteFilter(selectedFilter.id)}>
                  <DeleteIcon />
                </IconButton>
              )}
            </Box>
            {selectedFilter && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 2 }}>
                  Define your filter conditions below
                </Typography>
                <FilterBuilder
                  filter={selectedFilter}
                  onFilterChange={(name: string, query: string) => handleUpdateFilter(selectedFilter.id, name, query)}
                />
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>

      <Dialog open={isCreateDialogOpen} onClose={() => setIsCreateDialogOpen(false)}>
        <DialogTitle>Create New Filter</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Filter Name"
            fullWidth
            value={newFilterName}
            onChange={(e) => setNewFilterName(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateNewFilter} variant="contained" color="primary">
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default Filters;
