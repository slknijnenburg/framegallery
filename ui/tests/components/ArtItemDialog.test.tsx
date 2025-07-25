import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import ArtItemDialog from '../../src/components/ArtItemDialog';
import Image from '../../src/models/Image';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock Image data
const mockImage: Image = {
  id: '123',
  filename: 'test-image.jpg',
  created_at: '2023-01-01T12:00:00Z',
  thumbnail_path: 'thumbnails/test-image.jpg',
  file_path: 'images/test-image.jpg',
  display_duration: 300,
  matte_id: 'shadowbox_black', // Initial style: shadowbox, color: black
  portrait_matte_id: 'shadowbox_black',
  horizontal_alignment: 'center',
  vertical_alignment: 'center',
  artist: 'Test Artist',
  title: 'Test Title',
  description: 'Test Description',
  year: 2023,
};

describe('ArtItemDialog', () => {
  const mockOnClose = jest.fn();

  beforeEach(() => {
    // Clear mocks before each test
    mockOnClose.mockClear();
    mockedAxios.patch.mockClear();
    mockedAxios.patch.mockResolvedValue({}); // Default mock response
  });

  test('renders correctly when open and displays image filename', () => {
    render(<ArtItemDialog open={true} image={mockImage} onClose={mockOnClose} />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(`Item properties for ${mockImage.filename}`)).toBeInTheDocument();
    expect(screen.getByLabelText('Matte style:')).toBeInTheDocument();
    expect(screen.getByLabelText('Matte color:')).toBeInTheDocument();
  });

  test('initializes selects with values from image.matte_id', () => {
    render(<ArtItemDialog open={true} image={mockImage} onClose={mockOnClose} />);

    // Check initial selected values by text content (shadowbox, black)
    expect(screen.getByRole('combobox', { name: 'Matte style:' })).toHaveTextContent('Shadowbox');
    expect(screen.getByRole('combobox', { name: 'Matte color:' })).toHaveTextContent('Black');
  });

  test('calls onClose when Cancel button is clicked', () => {
    render(<ArtItemDialog open={true} image={mockImage} onClose={mockOnClose} />);

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('calls API and onClose when Submit button is clicked with changed values', async () => {
    render(<ArtItemDialog open={true} image={mockImage} onClose={mockOnClose} />);

    // Change style to 'flexible'
    const styleSelect = screen.getByRole('combobox', { name: 'Matte style:' });
    fireEvent.mouseDown(styleSelect); // Open the dropdown
    const listboxStyle = await screen.findByRole('listbox'); // Wait for listbox
    fireEvent.click(within(listboxStyle).getByRole('option', { name: 'Flexible' }));

    // Change color to 'antique'
    const colorSelect = screen.getByRole('combobox', { name: 'Matte color:' });
    fireEvent.mouseDown(colorSelect); // Open the dropdown
    const listboxColor = await screen.findByRole('listbox'); // Wait for listbox
    fireEvent.click(within(listboxColor).getByRole('option', { name: 'Antique' }));

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

    // Wait for async operations (API call)
    await waitFor(() => {
      expect(mockedAxios.patch).toHaveBeenCalledTimes(1);
    });

    // Check API call details
    expect(mockedAxios.patch).toHaveBeenCalledWith(
      `/api/available-art/${mockImage.id}`,
      {
        matte_id: 'flexible_antique',
        portrait_matte_id: 'flexible_antique', // Assumes portrait updates too
      }
    );

    // Check if onClose was called
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('handles "none" matte style correctly on submit', async () => {
    render(<ArtItemDialog open={true} image={mockImage} onClose={mockOnClose} />);

    // Ensure dialog is rendered before interacting
    await screen.findByRole('dialog');

    // Change style to 'None'
    const styleSelect = screen.getByRole('combobox', { name: 'Matte style:' });
    fireEvent.mouseDown(styleSelect);
    const listboxStyle = await screen.findByRole('listbox'); // Wait for listbox
    fireEvent.click(within(listboxStyle).getByRole('option', { name: 'None' }));

    // Submit the form
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

    await waitFor(() => {
      expect(mockedAxios.patch).toHaveBeenCalledTimes(1);
    });

    expect(mockedAxios.patch).toHaveBeenCalledWith(
      `/api/available-art/${mockImage.id}`,
      {
        matte_id: 'none',
        portrait_matte_id: 'none',
      }
    );
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  test('does not render dialog content when open is false', () => {
    render(<ArtItemDialog open={false} image={mockImage} onClose={mockOnClose} />);
    // The Dialog component itself might still be in the DOM but hidden
    // Check for absence of a key element instead
    expect(screen.queryByText(`Item properties for ${mockImage.filename}`)).not.toBeInTheDocument();
  });
});
