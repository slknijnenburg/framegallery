import {Field, formatQuery, QueryBuilder, RuleGroupType} from 'react-querybuilder';
import 'react-querybuilder/dist/query-builder.css';
import React from 'react';
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
    selectedFilter?: Filter | undefined;
    updateFilterHandler?: (id: string, name: string, rule: string) => void; // eslint-disable-line no-unused-vars, @typescript-eslint/no-unused-vars
}

const defaultFilter: RuleGroupType = {id: 'root', combinator: 'and', rules: []};

const Filters = ({selectedFilter, updateFilterHandler}: FilterBuilderProps) => {
    const [query, setQuery] = useState<RuleGroupType>(defaultFilter);
    const [filterName, setFilterName] = useState<string>(selectedFilter?.name || '');

    useEffect(() => {
        if (selectedFilter) {
            const jsonParsedFilter = JSON.parse(
                selectedFilter.query || '{"id":"root","combinator":"and","rules":[]}',
            ) as RuleGroupType;
            setQuery(jsonParsedFilter);
            setFilterName(selectedFilter.name);
        } else {
            setQuery(defaultFilter);
            setFilterName('');
        }
    }, [selectedFilter]);

    const updateFilter = (): void => {
        if (updateFilterHandler && selectedFilter) {
            updateFilterHandler(selectedFilter.id, filterName, JSON.stringify(query));
        }
    };

    const removeAllFilters = (): void => {
        setQuery(defaultFilter);
    };

    return (
        <>
            <Stack spacing={2}>
                <Container sx={{padding: 2}}>
                    <Stack direction={'column'} spacing={2}>
                        <QueryBuilder fields={fields} query={query} onQueryChange={setQuery}/>
                        <FormControl>
                            <Stack direction={'row'} spacing={2}>
                                <Button variant={'contained'} onClick={updateFilter}>
                                    Save filter
                                </Button>
                                <Button variant={'outlined'} onClick={removeAllFilters}>
                                    Clear filters
                                </Button>
                            </Stack>
                        </FormControl>
                    </Stack>
                </Container>
                <Container>
                    <h2>JSON</h2>
                    <pre>{formatQuery(query)}</pre>
                    <h2>SQL</h2>
                    <pre>{formatQuery(query, 'parameterized_named').sql}</pre>
                </Container>
            </Stack>
        </>
    );
};
export default Filters;
