import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { describe, it, expect } from '@jest/globals';
import TvFileList from '../../src/components/TvFileList';
import { TvFile } from '../../src/models/TvFile';

describe('TvFileList', () => {
  const mockFiles: TvFile[] = [
    {
      content_id: 'MY-F0001',
      file_name: 'Sunset Photo',
      file_type: 'JPEG',
      file_size: 2048576,
      date: '2024-01-15',
      category_id: 'MY-C0002',
      thumbnail_available: true,
      matte: 'none',
    },
    {
      content_id: 'MY-F0002',
      file_name: 'Beach Scene',
      file_type: 'PNG',
      file_size: 3145728,
      date: '2024-01-16',
      category_id: 'MY-C0002',
      thumbnail_available: false,
      matte: 'shadowbox_black',
    },
  ];

  it('should render loading state', () => {
    render(<TvFileList files={[]} loading={true} />);

    expect(screen.getByLabelText('TV files loading')).toBeInTheDocument();

    // Should show skeleton rows
    const skeletons = screen.getAllByRole('row');
    expect(skeletons.length).toBeGreaterThan(1); // Header + skeleton rows
  });

  it('should render empty state when no files', () => {
    render(<TvFileList files={[]} loading={false} />);

    expect(screen.getByText('No files found')).toBeInTheDocument();
    expect(screen.getByText('No files available on the TV.')).toBeInTheDocument();
  });

  it('should render empty state with category context', () => {
    render(<TvFileList files={[]} loading={false} category="User Content" />);

    expect(screen.getByText('No files found')).toBeInTheDocument();
    expect(screen.getByText('No files available in the User Content category.')).toBeInTheDocument();
  });

  it('should render files list correctly', () => {
    render(<TvFileList files={mockFiles} loading={false} category="User Content" />);

    // Check file count
    expect(screen.getByText('2 files found')).toBeInTheDocument();

    // Check category chip
    expect(screen.getByText('Category: User Content')).toBeInTheDocument();

    // Check table headers
    expect(screen.getByText('File Name')).toBeInTheDocument();
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Size')).toBeInTheDocument();
    expect(screen.getByText('Date')).toBeInTheDocument();
    expect(screen.getByText('Thumbnail')).toBeInTheDocument();
    expect(screen.getByText('Matte')).toBeInTheDocument();

    // Check first file data
    expect(screen.getByText('Sunset Photo')).toBeInTheDocument();
    expect(screen.getByText('ID: MY-F0001')).toBeInTheDocument();
    expect(screen.getByText('JPEG')).toBeInTheDocument();
    expect(screen.getByText('2.0 MB')).toBeInTheDocument();

    // Check second file data
    expect(screen.getByText('Beach Scene')).toBeInTheDocument();
    expect(screen.getByText('ID: MY-F0002')).toBeInTheDocument();
    expect(screen.getByText('PNG')).toBeInTheDocument();
    expect(screen.getByText('3.0 MB')).toBeInTheDocument();
  });

  it('should handle files with null values gracefully', () => {
    const fileWithNulls: TvFile[] = [
      {
        content_id: 'MY-F0003',
        file_name: 'Test Photo',
        file_type: 'JPEG',
        file_size: null,
        date: null,
        category_id: 'MY-C0002',
        thumbnail_available: null,
        matte: null,
      },
    ];

    render(<TvFileList files={fileWithNulls} loading={false} />);

    expect(screen.getByText('Test Photo')).toBeInTheDocument();
    expect(screen.getByText('JPEG')).toBeInTheDocument(); // File type is provided
    expect(screen.getAllByText('Unknown')).toHaveLength(3); // For file size, date, and thumbnail
    expect(screen.getByText('None')).toBeInTheDocument(); // For matte
  });

  it('should display thumbnail availability icons correctly', () => {
    render(<TvFileList files={mockFiles} loading={false} />);

    // First file has thumbnail available (should have success icon)
    const successIcon = screen.getByTitle('Thumbnail available');
    expect(successIcon).toBeInTheDocument();

    // Second file has no thumbnail (should have error icon)
    const errorIcon = screen.getByTitle('No thumbnail');
    expect(errorIcon).toBeInTheDocument();
  });

  it('should format matte names correctly', () => {
    render(<TvFileList files={mockFiles} loading={false} />);

    // First file has "none" matte
    expect(screen.getByText('None')).toBeInTheDocument();

    // Second file has "shadowbox_black" matte (should be formatted)
    expect(screen.getByText('shadowbox black')).toBeInTheDocument();
  });

  it('should handle single file count correctly', () => {
    const singleFile = [mockFiles[0]];
    render(<TvFileList files={singleFile} loading={false} />);

    expect(screen.getByText('1 file found')).toBeInTheDocument();
  });

  it('should not show category chip when category is not provided', () => {
    render(<TvFileList files={mockFiles} loading={false} />);

    expect(screen.queryByText(/Category:/)).not.toBeInTheDocument();
  });
});
