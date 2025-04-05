import {Field, formatQuery, QueryBuilder, RuleGroupType} from 'react-querybuilder';
import 'react-querybuilder/dist/query-builder.css';
import { useEffect, useState} from 'react';
import {Stack} from '@mui/material';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import Button from '@mui/material/Button';
import {Filter} from './Filter';

const fields: Field[] = [
    {name: 'directory', label: 'Directory'},
    {name: 'file_name', label: 'File name'},
    {name: 'aspect_ratio_width', label: 'Aspect ratio width'},
    {name: 'aspect_ratio_height', label: 'Aspect ratio height'},
];

interface FilterBuilderProps {
    filter: Filter;
    onFilterChange: (name: string, query: string) => void;
}

const defaultFilter: RuleGroupType = {id: 'root', combinator: 'and', rules: []};

const FilterBuilder = ({filter, onFilterChange}: FilterBuilderProps) => {
    const [query, setQuery] = useState<RuleGroupType>(defaultFilter);
    const [filterName, setFilterName] = useState<string>(filter.name);

    useEffect(() => {
        if (filter) {
            const jsonParsedFilter = JSON.parse(
                filter.query || '{"id":"root","combinator":"and","rules":[]}',
            ) as RuleGroupType;
            setQuery(jsonParsedFilter);
            setFilterName(filter.name);
        } else {
            setQuery(defaultFilter);
            setFilterName('');
        }
    }, [filter]);

    const handleQueryChange = (newQuery: RuleGroupType): void => {
        setQuery(newQuery);
    };

    const handleSave = (): void => {
        onFilterChange(filterName, JSON.stringify(query));
    };

    const removeAllFilters = (): void => {
        setQuery(defaultFilter);
    };

    return (
        <Container>
            <FormControl fullWidth sx={{mb: 2}}>
                <Stack spacing={2}>
                    <QueryBuilder
                        fields={fields}
                        query={query}
                        onQueryChange={handleQueryChange}
                    />
                    <Stack direction="row" spacing={2}>
                        <Button variant="contained" color="primary" onClick={handleSave}>
                            Save Filter
                        </Button>
                        <Button variant="outlined" onClick={removeAllFilters}>
                            Remove all filters
                        </Button>
                    </Stack>
                    <Stack spacing={1}>
                        <h2>JSON</h2>
                        <pre>{formatQuery(query)}</pre>
                        <h2>SQL</h2>
                        <pre>{formatQuery(query, 'parameterized_named').sql}</pre>
                    </Stack>
                </Stack>
            </FormControl>
        </Container>
    );
};

export default FilterBuilder;
