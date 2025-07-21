import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import FrameDisplayPreview from '../../src/components/FrameDisplayPreview';
import Image from '../../src/models/Image';

// Mock the App module to control API_BASE_URL
jest.mock('../../src/App', () => ({
    API_BASE_URL: 'http://mock-api.com',
}));

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock Image data
const mockNextImage: Image = {
    id: '456',
    filename: 'next-image.jpg',
    created_at: '2023-02-01T12:00:00Z',
    thumbnail_path: 'thumbnails/next-image.jpg',
    file_path: 'images/next-image.jpg',
    display_duration: 600,
    matte_id: 'flexible_white',
    portrait_matte_id: 'flexible_white',
    horizontal_alignment: 'left',
    vertical_alignment: 'top',
    artist: 'Next Artist',
    title: 'Next Title',
    description: 'Next Description',
    year: 2024,
};

describe('FrameDisplayPreview', () => {
    const mockImageUrl = 'http://mock-images.com/current.jpg';
    const mockOnNext = jest.fn();
    let consoleErrorSpy: jest.SpyInstance;

    beforeEach(() => {
        mockOnNext.mockClear();
        mockedAxios.post.mockClear();
        // Default successful response
        mockedAxios.post.mockResolvedValue({ data: mockNextImage });
        // Spy on console.error
        consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        // Restore console.error spy
        consoleErrorSpy.mockRestore();
    });

    test('renders image and next button correctly', () => {
        render(<FrameDisplayPreview imageUrl={mockImageUrl} onNext={mockOnNext} />);

        const imgElement = screen.getByRole('img');
        expect(imgElement).toBeInTheDocument();
        expect(imgElement).toHaveAttribute('src', mockImageUrl);

        expect(screen.getByRole('button', { name: 'next image' })).toBeInTheDocument();
    });

    test('calls API and onNext callback when next button is clicked', async () => {
        render(<FrameDisplayPreview imageUrl={mockImageUrl} onNext={mockOnNext} />);

        fireEvent.click(screen.getByRole('button', { name: 'next image' }));

        // Wait for axios call and subsequent state update/callback
        await waitFor(() => {
            expect(mockedAxios.post).toHaveBeenCalledTimes(1);
        });

        expect(mockedAxios.post).toHaveBeenCalledWith('http://mock-api.com/api/images/next');

        await waitFor(() => {
             expect(mockOnNext).toHaveBeenCalledTimes(1);
        });
        expect(mockOnNext).toHaveBeenCalledWith(mockNextImage);
    });

    test('does not render next button when onNext is not provided', () => {
        render(<FrameDisplayPreview imageUrl={mockImageUrl} />); // No onNext prop

        expect(screen.queryByRole('button', { name: 'next image' })).not.toBeInTheDocument();
    });

    test('handles API error and does not call onNext', async () => {
        const errorMessage = 'Network Error';
        mockedAxios.post.mockRejectedValueOnce(new Error(errorMessage));

        render(<FrameDisplayPreview imageUrl={mockImageUrl} onNext={mockOnNext} />);

        fireEvent.click(screen.getByRole('button', { name: 'next image' }));

        await waitFor(() => {
            expect(mockedAxios.post).toHaveBeenCalledTimes(1);
        });

        expect(mockedAxios.post).toHaveBeenCalledWith('http://mock-api.com/api/images/next');
        expect(mockOnNext).not.toHaveBeenCalled();

        // Check if console.error was called
        expect(consoleErrorSpy).toHaveBeenCalled();
        // Optionally check the error message structure if needed
        // expect(consoleErrorSpy).toHaveBeenCalledWith('Error fetching next image:', expect.any(Error));
    });
});
