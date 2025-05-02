import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SettingsStatus from '../../src/components/SettingsStatus';
import { useSettings } from '../../src/SettingsContext';
import { Settings } from '../../src/models/Settings';
import Image from '../../src/models/Image'; 
import { Filter } from '../../src/components/Filters/Filter'; 

jest.mock('../../src/SettingsContext');
const mockUseSettings = useSettings as jest.MockedFunction<typeof useSettings>; 
const mockUpdateSetting = jest.fn(); 

const mockImage: Image = {
    id: 1, 
    filename: 'active-image.jpg',
    filepath: '/path/to/active-image.jpg',
    filetype: 'image/jpeg',
    thumbnail_path: '/path/to/thumb.jpg',
    width: 1920,
    height: 1080,
    aspect_width: 16,
    aspect_height: 9,
    matte_id: 'shadowbox_black', 
};

const mockFilter: Filter = {
  id: 1,
  name: 'Sample Filter',
  query: '{"tag":"landscape"}', 
};

const mockSettings: Settings = {
  slideshow_enabled: true,
  slideshow_interval: 30,
  current_active_image: mockImage,
  current_active_image_since: '2023-10-27T10:00:00Z', 
  active_filter: mockFilter,
};

const mockSettingsNoFilter: Settings = {
    ...mockSettings,
    active_filter: null,
};

describe('SettingsStatus Component', () => {
  beforeEach(() => {
    mockUseSettings.mockClear();
    mockUpdateSetting.mockClear(); 
  });

  test('renders loading state', () => {
    mockUseSettings.mockReturnValue({ settings: null, loading: true, error: null, updateSetting: mockUpdateSetting });
    render(<SettingsStatus />);
    expect(screen.getByText('Loading settings...')).toBeInTheDocument();
  });

  test('renders error state', () => {
    const errorMessage = 'Failed to fetch settings';
    mockUseSettings.mockReturnValue({ settings: null, loading: false, error: errorMessage, updateSetting: mockUpdateSetting });
    render(<SettingsStatus />);
    expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
  });

  test('renders settings correctly when loaded', () => {
    mockUseSettings.mockReturnValue({ settings: mockSettings, loading: false, error: null, updateSetting: mockUpdateSetting });
    render(<SettingsStatus />);

    expect(screen.getByText(/Slideshow:/)).toBeInTheDocument();
    expect(screen.getByText(`Enabled (${mockSettings.slideshow_interval}s)`)).toBeInTheDocument();

    expect(screen.getByText(/Active Image:/)).toBeInTheDocument();
    expect(screen.getByText(mockSettings.current_active_image.filename)).toBeInTheDocument();

    expect(screen.getByText(/Active Image Since:/)).toBeInTheDocument();
    expect(screen.getByText(/10\/27\/2023/)).toBeInTheDocument(); 
    expect(screen.getByText(/:00:00/)).toBeInTheDocument(); 

    expect(screen.getByText(/Active Filter:/)).toBeInTheDocument();
    expect(screen.getByText(mockSettings.active_filter!.name)).toBeInTheDocument(); 
  });

   test('renders slideshow disabled correctly', () => {
        const disabledSettings = { ...mockSettings, slideshow_enabled: false };
        mockUseSettings.mockReturnValue({ settings: disabledSettings, loading: false, error: null, updateSetting: mockUpdateSetting });
        render(<SettingsStatus />);

        expect(screen.getByText(/Slideshow:/)).toBeInTheDocument();
        expect(screen.getByText('Disabled')).toBeInTheDocument();
   });

    test('renders "None" when active filter is null', () => {
        mockUseSettings.mockReturnValue({ settings: mockSettingsNoFilter, loading: false, error: null, updateSetting: mockUpdateSetting });
        render(<SettingsStatus />);

        expect(screen.getByText(/Active Filter:/)).toBeInTheDocument();
        expect(screen.getByText('None')).toBeInTheDocument();
    });
});
