import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FilterBuilder from '../../../src/components/Filters/FilterBuilder';
import { Filter } from '../../../src/components/Filters/Filter';
import { RuleGroupType } from 'react-querybuilder';

// Mock filter data
const emptyFilter: Filter = {
    id: 0, // Use number
    name: 'Empty Filter',
    query: '', // Equivalent to default
};

const initialFilterQuery: RuleGroupType = {
    id: 'root',
    combinator: 'and',
    rules: [
        { field: 'directory', operator: 'beginsWith', value: '/images' },
    ],
};

const existingFilter: Filter = {
    id: 1, // Use number
    name: 'Existing Filter',
    query: JSON.stringify(initialFilterQuery),
};

const defaultQueryString = JSON.stringify({ id: 'root', combinator: 'and', rules: [] });

describe('FilterBuilder', () => {
    const mockOnFilterChange = jest.fn();
    let consoleErrorSpy: jest.SpyInstance;
    let originalConsoleError: any; // eslint-disable-line @typescript-eslint/no-explicit-any

    beforeEach(() => {
        mockOnFilterChange.mockClear();
        originalConsoleError = console.error; // Store original console.error
        consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation((message, ...args) => {
             if (!message?.includes('Warning: Each child in a list should have a unique "key" prop.')) {
                 originalConsoleError(message, args); // Call the original console.error
             }
        });
    });

    afterEach(() => {
        consoleErrorSpy.mockRestore();
        console.error = originalConsoleError; // Restore original console.error
    });

    test('renders QueryBuilder and control buttons', () => {
        render(<FilterBuilder filter={emptyFilter} onFilterChange={mockOnFilterChange} />);

        // Check that the main query builder elements are rendered
        expect(screen.getByRole('form')).toBeInTheDocument();
        // Corrected name: Combinators (plural)
        expect(screen.getByRole('combobox', { name: 'Combinators' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '+ Rule' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: '+ Group' })).toBeInTheDocument();

        // Check that the custom control buttons are rendered
        expect(screen.getByRole('button', { name: 'Save Filter' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Remove all filters' })).toBeInTheDocument();

        // Check for preview headers
        expect(screen.getByRole('heading', { name: 'JSON' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'SQL' })).toBeInTheDocument();
    });

    test('calls onFilterChange with initial filter data on save', () => {
        render(<FilterBuilder filter={existingFilter} onFilterChange={mockOnFilterChange} />);

        fireEvent.click(screen.getByRole('button', { name: 'Save Filter' }));

        expect(mockOnFilterChange).toHaveBeenCalledTimes(1);
        expect(mockOnFilterChange).toHaveBeenCalledWith(existingFilter.name, existingFilter.query);
    });

    test('calls onFilterChange with empty query after removing filters', () => {
        render(<FilterBuilder filter={existingFilter} onFilterChange={mockOnFilterChange} />);

        fireEvent.click(screen.getByRole('button', { name: 'Remove all filters' }));
        fireEvent.click(screen.getByRole('button', { name: 'Save Filter' }));

        expect(mockOnFilterChange).toHaveBeenCalledTimes(1);
        expect(mockOnFilterChange).toHaveBeenCalledWith(existingFilter.name, defaultQueryString);
    });

    test('calls onFilterChange with updated query after adding a rule', async () => {
        render(<FilterBuilder filter={emptyFilter} onFilterChange={mockOnFilterChange} />);

        // Simulate adding a rule - This depends heavily on react-querybuilder's DOM structure
        // 1. Click 'Add Rule'
        fireEvent.click(screen.getByRole('button', { name: '+ Rule' }));

        // 2. Select field (assuming 'Directory' is the default or first option)
        // No explicit change needed if default is okay

        // 3. Select operator (change from '=' to 'contains')
        // Find the operator selector for the first rule
        const operatorSelects = screen.getAllByRole('combobox', { name: 'Operators' });
        fireEvent.change(operatorSelects[0], { target: { value: 'contains' } });

        // 4. Enter value
        const valueInputs = screen.getAllByRole('textbox'); // Gets all text inputs
        // Find the specific input for the rule's value. This might need a more specific selector
        // if there are other text boxes. Assuming it's the first relevant one.
        fireEvent.change(valueInputs[0], { target: { value: 'test/path' } });

        // 5. Click Save
        fireEvent.click(screen.getByRole('button', { name: 'Save Filter' }));

        // Verify the callback
        expect(mockOnFilterChange).toHaveBeenCalledTimes(1);

        // Check if the mock function was called with the correct name and *any* query object/string
        // (since the exact structure might be complex or change)
        await waitFor(() => {
            expect(mockOnFilterChange).toHaveBeenCalledWith('Empty Filter', expect.any(String)); // Expect a string now
        });
    });

    test('initializes with the query from the filter prop', () => {
        render(<FilterBuilder filter={existingFilter} onFilterChange={mockOnFilterChange} />);

        // Check if the initial rule is reflected in the previews (e.g., JSON preview)
        // This is an indirect way to check initialization
        const jsonPreview = screen.getByRole('heading', { name: 'JSON' }).nextElementSibling;
        expect(jsonPreview).toHaveTextContent('"field": "directory"');
        expect(jsonPreview).toHaveTextContent('"operator": "beginsWith"');
        expect(jsonPreview).toHaveTextContent('"value": "/images"');
    });
});
