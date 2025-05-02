import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImageGrid from '../../src/components/ImageGrid';
import Image from '../../src/models/Image';

// Mock ArtItemCard component
jest.mock('../../src/components/ArtItemCard', () => ({
    __esModule: true,
    default: jest.fn(({ item }) => <div data-testid={`art-item-${item.id}`}>{item.filename}</div>),
}));

// Helper to create mock images
const createMockImages = (count: number): Image[] => {
    return Array.from({ length: count }, (_, i) => ({
        id: `img-${i + 1}`,
        filename: `image${i + 1}.jpg`,
        created_at: '2023-01-01T12:00:00Z',
        thumbnail_path: `thumb${i + 1}.jpg`,
        file_path: `file${i + 1}.jpg`,
        display_duration: 300,
        matte_id: 'shadowbox_black',
        portrait_matte_id: 'shadowbox_black',
        horizontal_alignment: 'center',
        vertical_alignment: 'center',
        artist: `Artist ${i + 1}`,
        title: `Title ${i + 1}`,
        description: `Description ${i + 1}`,
        year: 2023,
    }));
};

describe('ImageGrid', () => {
    const initialVisibleCount = 18;
    const loadMoreIncrement = 6;

    test('renders initial set of items and load more chip', () => {
        const mockItems = createMockImages(25);
        render(<ImageGrid items={mockItems} />);

        // Check initial items rendered
        expect(screen.getAllByTestId(/art-item-/)).toHaveLength(initialVisibleCount);
        expect(screen.getByText(mockItems[0].filename)).toBeInTheDocument();
        expect(screen.getByText(mockItems[initialVisibleCount - 1].filename)).toBeInTheDocument();
        expect(screen.queryByText(mockItems[initialVisibleCount].filename)).not.toBeInTheDocument();

        // Check "Load more" chip is visible
        expect(screen.getByRole('button', { name: 'Load more images' })).toBeInTheDocument();
        // Check "All displayed" chip is not visible
        expect(screen.queryByText('All images are displayed')).not.toBeInTheDocument();
    });

    test('loads more items when Load more chip is clicked', () => {
        const mockItems = createMockImages(25);
        render(<ImageGrid items={mockItems} />);

        // Initial check
        expect(screen.getAllByTestId(/art-item-/)).toHaveLength(initialVisibleCount);

        // Click "Load more"
        const loadMoreButton = screen.getByRole('button', { name: 'Load more images' });
        fireEvent.click(loadMoreButton);

        // Check items after first load more
        const firstLoadCount = initialVisibleCount + loadMoreIncrement;
        expect(screen.getAllByTestId(/art-item-/)).toHaveLength(firstLoadCount); // 18 + 6 = 24
        expect(screen.getByText(mockItems[firstLoadCount - 1].filename)).toBeInTheDocument();
        expect(screen.queryByText(mockItems[firstLoadCount].filename)).not.toBeInTheDocument(); // 25th item shouldn't be there yet

        // "Load more" should still be visible
        expect(screen.getByRole('button', { name: 'Load more images' })).toBeInTheDocument();
        expect(screen.queryByText('All images are displayed')).not.toBeInTheDocument();

        // Click "Load more" again
        fireEvent.click(loadMoreButton);

        // Check items after second load more (all items)
        expect(screen.getAllByTestId(/art-item-/)).toHaveLength(mockItems.length); // 25
        expect(screen.getByText(mockItems[mockItems.length - 1].filename)).toBeInTheDocument();

        // "Load more" should be hidden, "All displayed" should be visible
        expect(screen.queryByRole('button', { name: 'Load more images' })).not.toBeInTheDocument();
        expect(screen.getByText('All images are displayed')).toBeInTheDocument();
    });

    test('shows all items and "All displayed" chip if items < initial count', () => {
        const mockItems = createMockImages(10);
        render(<ImageGrid items={mockItems} />);

        expect(screen.getAllByTestId(/art-item-/)).toHaveLength(mockItems.length);
        expect(screen.queryByRole('button', { name: 'Load more images' })).not.toBeInTheDocument();
        expect(screen.getByText('All images are displayed')).toBeInTheDocument();
    });

    test('shows "All displayed" chip if items array is empty', () => {
        const mockItems: Image[] = [];
        render(<ImageGrid items={mockItems} />);

        expect(screen.queryAllByTestId(/art-item-/)).toHaveLength(0);
        expect(screen.queryByRole('button', { name: 'Load more images' })).not.toBeInTheDocument();
        expect(screen.getByText('All images are displayed')).toBeInTheDocument();
    });

    test('adds and removes scroll event listener', () => {
        const mockItems = createMockImages(25);
        const addSpy = jest.spyOn(window, 'addEventListener');
        const removeSpy = jest.spyOn(window, 'removeEventListener');

        const { unmount } = render(<ImageGrid items={mockItems} />);

        // Check if added on mount
        expect(addSpy).toHaveBeenCalledWith('scroll', expect.any(Function)); 

        unmount();

        // Check if removed on unmount
        expect(removeSpy).toHaveBeenCalledWith('scroll', expect.any(Function));

        addSpy.mockRestore();
        removeSpy.mockRestore();
    });

    // Note: Testing the actual scroll event triggering loadMore is complex
    // and often requires mocking scroll properties. Testing the click 
    // handler covers the core loadMore logic.
});
