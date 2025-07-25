import {Field, formatQuery, QueryBuilder, RuleGroupType, generateID} from 'react-querybuilder';
import 'react-querybuilder/dist/query-builder.css';
import React, {useEffect, useState} from 'react';
import {Stack} from '@mui/material';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import Button from '@mui/material/Button';
import {Filter} from './Filter';

const fields: Field[] = [
    {
        name: 'directory',
        label: 'Directory',
        valueEditorType: 'text',
        datatype: 'string',
        operators: [
            { name: '=', value: '=', label: '=' },
            { name: '!=', value: '!=', label: '!=' },
            { name: 'contains', value: 'contains', label: 'contains' },
            { name: 'beginsWith', value: 'beginsWith', label: 'begins with' },
            { name: 'endsWith', value: 'endsWith', label: 'ends with' },
            { name: 'doesNotContain', value: 'doesNotContain', label: 'does not contain' },
            { name: 'doesNotBeginWith', value: 'doesNotBeginWith', label: 'does not begin with' },
            { name: 'doesNotEndWith', value: 'doesNotEndWith', label: 'does not end with' },
            { name: 'null', value: 'null', label: 'is null' },
            { name: 'notNull', value: 'notNull', label: 'is not null' },
            { name: 'in', value: 'in', label: 'in' },
            { name: 'notIn', value: 'notIn', label: 'not in' },
        ]
    },
    {
        name: 'file_name',
        label: 'File name',
        valueEditorType: 'text',
        datatype: 'string',
        operators: [
            { name: '=', value: '=', label: '=' },
            { name: '!=', value: '!=', label: '!=' },
            { name: 'contains', value: 'contains', label: 'contains' },
            { name: 'beginsWith', value: 'beginsWith', label: 'begins with' },
            { name: 'endsWith', value: 'endsWith', label: 'ends with' },
            { name: 'doesNotContain', value: 'doesNotContain', label: 'does not contain' },
            { name: 'doesNotBeginWith', value: 'doesNotBeginWith', label: 'does not begin with' },
            { name: 'doesNotEndWith', value: 'doesNotEndWith', label: 'does not end with' },
            { name: 'null', value: 'null', label: 'is null' },
            { name: 'notNull', value: 'notNull', label: 'is not null' },
            { name: 'in', value: 'in', label: 'in' },
            { name: 'notIn', value: 'notIn', label: 'not in' },
        ]
    },
    {
        name: 'aspect_ratio_width',
        label: 'Aspect ratio width',
        datatype: 'number',
        operators: [
            { name: '=', value: '=', label: '=' },
            { name: '!=', value: '!=', label: '!=' },
            { name: '>', value: '>', label: '>' },
            { name: '<', value: '<', label: '<' },
            { name: '>=', value: '>=', label: '>=' },
            { name: '<=', value: '<=', label: '<=' },
            { name: 'null', value: 'null', label: 'is null' },
            { name: 'notNull', value: 'notNull', label: 'is not null' },
        ]
    },
    {
        name: 'aspect_ratio_height',
        label: 'Aspect ratio height',
        datatype: 'number',
        operators: [
            { name: '=', value: '=', label: '=' },
            { name: '!=', value: '!=', label: '!=' },
            { name: '>', value: '>', label: '>' },
            { name: '<', value: '<', label: '<' },
            { name: '>=', value: '>=', label: '>=' },
            { name: '<=', value: '<=', label: '<=' },
            { name: 'null', value: 'null', label: 'is null' },
            { name: 'notNull', value: 'notNull', label: 'is not null' },
        ]
    },
];

interface FilterBuilderProps {
    filter: Filter;
    onFilterChange: (name: string, query: string) => void;
}

const defaultFilter: RuleGroupType = {id: generateID(), combinator: 'and', rules: []};

const FilterBuilder = ({filter, onFilterChange}: FilterBuilderProps) => {
    const [query, setQuery] = useState<RuleGroupType>(defaultFilter);
    const [filterName, setFilterName] = useState<string>(filter.name);

    useEffect(() => {
        if (filter) {
            const jsonParsedFilter = JSON.parse(
                filter.query || '{"id":"root","combinator":"and","rules":[]}',
            ) as RuleGroupType;

            // Ensure the parsed filter has an ID
            const filterWithId = {
                ...jsonParsedFilter,
                id: jsonParsedFilter.id || generateID()
            };

            setQuery(filterWithId);
            setFilterName(filter.name);
        } else {
            setQuery({...defaultFilter, id: generateID()});
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
        setQuery({...defaultFilter, id: generateID()});
    };

    return (
        <Container>
            <FormControl fullWidth sx={{mb: 2}}>
                <Stack spacing={2}>
                    <QueryBuilder
                        fields={fields}
                        query={query}
                        onQueryChange={handleQueryChange}
                        idGenerator={generateID}
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
