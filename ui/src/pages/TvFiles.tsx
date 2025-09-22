import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Stack,
  CircularProgress,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Tv as TvIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import TvFileList from '../components/TvFileList';
import { TvFile, TvCategory, TV_CATEGORIES } from '../models/TvFile';
import { tvFilesService, TvServiceError } from '../services/tvFilesService';

/**
 * Page component for displaying and managing TV files.
 */
const TvFiles: React.FC = () => {
  const [files, setFiles] = useState<TvFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isServiceUnavailable, setIsServiceUnavailable] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<TvCategory>(TV_CATEGORIES.USER_CONTENT);
  const [refreshing, setRefreshing] = useState(false);

  /**
   * Fetch TV files for the selected category.
   */
  const fetchTvFiles = useCallback(async (category: TvCategory, isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
        setError(null);
      } else {
        setLoading(true);
        setError(null);
        setIsServiceUnavailable(false);
      }

      const tvFiles = await tvFilesService.getTvFiles(category);
      setFiles(tvFiles);
      setError(null);
      setIsServiceUnavailable(false);

    } catch (err) {
      console.error('Error fetching TV files:', err);

      if (err instanceof TvServiceError) {
        setError(err.message);
        setIsServiceUnavailable(err.isServiceUnavailable);
      } else {
        setError('An unexpected error occurred while fetching TV files.');
        setIsServiceUnavailable(false);
      }

      // On error, clear the files list
      setFiles([]);

    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  /**
   * Handle category change.
   */
  const handleCategoryChange = useCallback((category: TvCategory) => {
    setSelectedCategory(category);
    fetchTvFiles(category);
  }, [fetchTvFiles]);

  /**
   * Handle refresh button click.
   */
  const handleRefresh = useCallback(() => {
    fetchTvFiles(selectedCategory, true);
  }, [fetchTvFiles, selectedCategory]);

  /**
   * Handle file deletion.
   */
  const handleDelete = useCallback(async (contentId: string) => {
    try {
      await tvFilesService.deleteTvFile(contentId);
      // Refresh the file list after successful deletion
      await fetchTvFiles(selectedCategory, true);
    } catch (error) {
      console.error('Failed to delete file:', error);
      // Error is already handled by the service, just re-throw to show loading state properly
      throw error;
    }
  }, [fetchTvFiles, selectedCategory]);

  // Initial load
  useEffect(() => {
    fetchTvFiles(selectedCategory);
  }, [fetchTvFiles, selectedCategory]);

  // Get available categories for the dropdown
  const availableCategories = tvFilesService.getAvailableCategories();

  return (
    <Container maxWidth="xl">
      <Box sx={{ my: 4 }}>
        {/* Page Header */}
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
          <TvIcon sx={{ fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h4" component="h1">
            Files on TV
          </Typography>
        </Stack>

        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          View and manage files currently available on your Samsung Frame TV.
        </Typography>

        {/* Controls */}
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={2}
          alignItems={{ xs: 'stretch', sm: 'center' }}
          sx={{ mb: 3 }}
        >
          {/* Category selector */}
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel id="category-select-label">Category</InputLabel>
            <Select
              labelId="category-select-label"
              value={selectedCategory}
              label="Category"
              onChange={(e) => handleCategoryChange(e.target.value as TvCategory)}
              disabled={loading}
            >
              {availableCategories.map((category) => (
                <MenuItem key={category.id} value={category.id}>
                  {category.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Refresh button */}
          <Button
            variant="outlined"
            startIcon={refreshing ? <CircularProgress size={16} /> : <RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading || refreshing}
            sx={{ minWidth: 120 }}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </Stack>

        {/* Error Alert */}
        {error && (
          <Alert
            severity={isServiceUnavailable ? 'warning' : 'error'}
            icon={isServiceUnavailable ? <WarningIcon /> : <ErrorIcon />}
            sx={{ mb: 3 }}
            action={
              <Button
                color="inherit"
                size="small"
                onClick={handleRefresh}
                disabled={refreshing}
              >
                Retry
              </Button>
            }
          >
            <Typography variant="body2" component="div">
              <strong>
                {isServiceUnavailable ? 'TV Unavailable' : 'Error'}
              </strong>
            </Typography>
            <Typography variant="body2">
              {error}
            </Typography>
            {isServiceUnavailable && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Make sure your Samsung Frame TV is powered on and connected to the network.
              </Typography>
            )}
          </Alert>
        )}

        {/* Files List */}
        <TvFileList
          files={files}
          loading={loading}
          category={availableCategories.find(c => c.id === selectedCategory)?.name}
          onDelete={handleDelete}
        />

        {/* Additional Info */}
        {!loading && !error && files.length > 0 && (
          <Box sx={{ mt: 3, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">
              <strong>Note:</strong> This data is retrieved directly from your Samsung Frame TV.
              File availability and details may vary based on TV status and network connectivity.
            </Typography>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default TvFiles;
