import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Typography,
  Box,
  Skeleton,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  ImageOutlined as ImageIcon,
} from '@mui/icons-material';
import { TvFile } from '../models/TvFile';
import { tvFilesService } from '../services/tvFilesService';

interface TvFileListProps {
  /** Array of TV files to display */
  files: TvFile[];
  /** Whether the data is currently loading */
  loading?: boolean;
  /** Category being displayed for context */
  category?: string;
}

/**
 * Component for displaying a list of TV files in a table format.
 */
const TvFileList: React.FC<TvFileListProps> = ({ files, loading = false, category }) => {
  // Loading skeleton
  if (loading) {
    return (
      <TableContainer component={Paper} elevation={2}>
        <Table aria-label="TV files loading">
          <TableHead>
            <TableRow>
              <TableCell>File Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell align="right">Size</TableCell>
              <TableCell>Date</TableCell>
              <TableCell align="center">Thumbnail</TableCell>
              <TableCell>Matte</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Array.from({ length: 5 }).map((_, index) => (
              <TableRow key={`skeleton-${index}`}>
                <TableCell>
                  <Skeleton variant="text" width="60%" />
                </TableCell>
                <TableCell>
                  <Skeleton variant="text" width="40%" />
                </TableCell>
                <TableCell align="right">
                  <Skeleton variant="text" width="50%" />
                </TableCell>
                <TableCell>
                  <Skeleton variant="text" width="70%" />
                </TableCell>
                <TableCell align="center">
                  <Skeleton variant="circular" width={24} height={24} />
                </TableCell>
                <TableCell>
                  <Skeleton variant="text" width="60%" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }

  // Empty state
  if (files.length === 0) {
    return (
      <Paper elevation={2} sx={{ p: 4, textAlign: 'center' }}>
        <ImageIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No files found
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {category ? `No files available in the ${category} category.` : 'No files available on the TV.'}
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      {/* File count and category info */}
      <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          {files.length} file{files.length !== 1 ? 's' : ''} found
        </Typography>
        {category && (
          <Chip
            label={`Category: ${category}`}
            size="small"
            variant="outlined"
          />
        )}
      </Box>

      {/* Files table */}
      <TableContainer component={Paper} elevation={2}>
        <Table aria-label="TV files table">
          <TableHead>
            <TableRow>
              <TableCell>
                <Typography variant="subtitle2" fontWeight="medium">
                  File Name
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="subtitle2" fontWeight="medium">
                  Type
                </Typography>
              </TableCell>
              <TableCell align="right">
                <Typography variant="subtitle2" fontWeight="medium">
                  Size
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="subtitle2" fontWeight="medium">
                  Date
                </Typography>
              </TableCell>
              <TableCell align="center">
                <Typography variant="subtitle2" fontWeight="medium">
                  Thumbnail
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="subtitle2" fontWeight="medium">
                  Matte
                </Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {files.map((file) => (
              <TableRow
                key={file.content_id}
                hover
                sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
              >
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {file.file_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    ID: {file.content_id}
                  </Typography>
                </TableCell>

                <TableCell>
                  <Chip
                    label={file.file_type}
                    size="small"
                    color={file.file_type === 'JPEG' ? 'primary' : 'secondary'}
                    variant="outlined"
                  />
                </TableCell>

                <TableCell align="right">
                  <Typography variant="body2">
                    {tvFilesService.formatFileSize(file.file_size)}
                  </Typography>
                </TableCell>

                <TableCell>
                  <Typography variant="body2">
                    {tvFilesService.formatDate(file.date)}
                  </Typography>
                </TableCell>

                <TableCell align="center">
                  {file.thumbnail_available === true && (
                    <CheckCircleIcon
                      sx={{ color: 'success.main', fontSize: 20 }}
                      titleAccess="Thumbnail available"
                    />
                  )}
                  {file.thumbnail_available === false && (
                    <CancelIcon
                      sx={{ color: 'error.main', fontSize: 20 }}
                      titleAccess="No thumbnail"
                    />
                  )}
                  {file.thumbnail_available === null && (
                    <Typography variant="body2" color="text.secondary">
                      Unknown
                    </Typography>
                  )}
                </TableCell>

                <TableCell>
                  {file.matte && file.matte !== 'none' ? (
                    <Chip
                      label={file.matte.replace(/_/g, ' ')}
                      size="small"
                      variant="filled"
                      sx={{
                        textTransform: 'capitalize',
                        backgroundColor: 'grey.100',
                        color: 'text.primary',
                      }}
                    />
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      None
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default TvFileList;
