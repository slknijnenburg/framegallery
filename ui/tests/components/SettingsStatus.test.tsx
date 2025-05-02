import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SettingsStatus from '../../src/components/SettingsStatus';
import { useSettings } from '../../src/SettingsContext';
// import { Settings } from '../../src/models/Settings'; // Assuming Settings model exists
// import Image from '../../src/models/Image'; // Assuming Image model exists
// import { Filter } from '../../src/components/Filters/Filter'; // Assuming Filter model exists

// Mock the useSettings hook
jest.mock('../../src/SettingsContext');
const mockUseSettings = useSettings as jest.MockedFunction<typeof useSettings>;

// Helper function to create mock settings
const createMockSettings = (overrides: Partial<Settings> = {}): Settings => ({
    slideshow_interval: 300,
    slideshow_enabled: true,
    active_filter: {
        name: 'Test Filter',
        query: '{\"combinator\": \"and\", \"rules\": []}',
    },
    current_active_image: {
        id: 'img-1',
        filename: 'active-image.jpg',
        created_at: '2023-01-01T12:00:00Z',
        thumbnail_path: 'thumb.jpg',
        file_path: 'file.jpg',
        display_duration: 300,
        matte_id: 'shadowbox_black',
        portrait_matte_id: 'shadowbox_black',
        horizontal_alignment: 'center',
        vertical_alignment: 'center',
        artist: 'Artist',
        title: 'Title',
        description: 'Description',
        year: 2023,
    },
    available_art: [], // Not used by this component
    filters: [],       // Not used by this component
    version: '1.0.0',  // Not used by this component
    ...overrides,
});

describe('SettingsStatus', () => {
    beforeEach(() => {
        // Reset the mock before each test
        mockUseSettings.mockClear();
    });

    test('renders loading indicator when loading', () => {
        mockUseSettings.mockReturnValue({ settings: null, loading: true, error: null });
        render(<SettingsStatus />);
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
        expect(screen.queryByText(/Slideshow Interval/)).not.toBeInTheDocument(); // Check one element isn't there
    });

    test('renders error message when there is an error', () => {
        const errorMessage = 'Failed to fetch settings';
        mockUseSettings.mockReturnValue({ settings: null, loading: false, error: errorMessage });
        render(<SettingsStatus />);
        expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });

    test('renders nothing when settings are null and not loading/error', () => {
        mockUseSettings.mockReturnValue({ settings: null, loading: false, error: null });
        const { container } = render(<SettingsStatus />);
        // Check if the container is basically empty (or only contains the outer Box)
        // It shouldn't render the Paper element or its contents
        expect(container.querySelector('div[class*="MuiPaper-root"]')).not.toBeInTheDocument();
    });

    test('renders settings correctly when slideshow is enabled', () => {
        const mockSettings = createMockSettings({ slideshow_interval: 120 });
        mockUseSettings.mockReturnValue({ settings: mockSettings, loading: false, error: null });
        render(<SettingsStatus />);

        expect(screen.getByText('120 s')).toBeInTheDocument();
        expect(screen.getByTestId('CheckCircleIcon')).toBeInTheDocument(); // Success icon
        expect(screen.getByText('On')).toBeInTheDocument();
        expect(screen.getByText('active-image.jpg')).toBeInTheDocument();
        // Check tooltip for full filename
        expect(screen.getByTitle('active-image.jpg')).toBeInTheDocument();
        expect(screen.getByText('Test Filter')).toBeInTheDocument();
    });

    test('renders settings correctly when slideshow is disabled', () => {
        const mockSettings = createMockSettings({ slideshow_enabled: false });
        mockUseSettings.mockReturnValue({ settings: mockSettings, loading: false, error: null });
        render(<SettingsStatus />);

        expect(screen.getByTestId('CancelIcon')).toBeInTheDocument(); // Disabled icon
        expect(screen.getByText('Off')).toBeInTheDocument();
    });

    test('renders "None" when active image is null', () => {
        const mockSettings = createMockSettings({ current_active_image: null });
        mockUseSettings.mockReturnValue({ settings: mockSettings, loading: false, error: null });
        render(<SettingsStatus />);

        // Find the element associated with the InsertDriveFileIcon
        const icon = screen.getByTestId('InsertDriveFileIcon');
        const parentStack = icon.closest('div');
        const textElement = parentStack?.querySelector('p'); // Find Typography within the stack

        expect(textElement).toHaveTextContent('None');
        expect(screen.getByTitle('None')).toBeInTheDocument(); // Check tooltip too
    });

    test('renders "None" when active filter is null', () => {
        const mockSettings = createMockSettings({ active_filter: null });
        mockUseSettings.mockReturnValue({ settings: mockSettings, loading: false, error: null });
        render(<SettingsStatus />);

        // Find the element associated with the FilterListIcon
        const icon = screen.getByTestId('FilterListIcon');
        const parentStack = icon.closest('div');
        const textElement = parentStack?.querySelector('p');

        expect(textElement).toHaveTextContent('None');
    });
});
