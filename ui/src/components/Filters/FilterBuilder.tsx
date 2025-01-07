import { Field, formatQuery, QueryBuilder, RuleGroupType } from 'react-querybuilder';
import 'react-querybuilder/dist/query-builder.css';
import { ChangeEvent, useEffect, useState } from "react";
import { Stack, TextField } from "@mui/material";
import Container from "@mui/material/Container";
import FormControl from "@mui/material/FormControl";
import Button from "@mui/material/Button";
import { Filter } from "./Filter";

const fields: Field[] = [
    {name: 'directory', label: 'Directory'},
    {name: 'file_name', label: 'File name'},
    {name: 'aspect_ratio_width', label: 'Aspect ratio width'},
    {name: 'aspect_ratio_height', label: 'Aspect ratio height'},
];

interface FilterBuilderProps {
    selectedFilter?: Filter | undefined,
    saveFilterHandler?: (name: string, rule: string) => void
}

const defaultFilter: RuleGroupType = {
    id: 'root', combinator: 'and', rules: [
        {
            "id": "75d80eb5-edf8-4dd3-a49c-ba794f62225c",
            "field": "aspect_ratio_width",
            "operator": "=",
            "valueSource": "value",
            "value": "16"
        }
    ]
};

const Filters = ({selectedFilter, saveFilterHandler}: FilterBuilderProps) => {
    const [query, setQuery] = useState<RuleGroupType>(defaultFilter);
    const [filterName, setFilterName] = useState<string>(selectedFilter?.name || '');

    useEffect(() => {
        if (selectedFilter) {
            const jsonParsedFilter = JSON.parse(selectedFilter.query || '{"id":"root","combinator":"and","rules":[]}') as RuleGroupType;
            setQuery(jsonParsedFilter);
            setFilterName(selectedFilter.name);
        } else {
            setQuery(defaultFilter);
            setFilterName('');
        }
    }, [selectedFilter]);

    console.log(query);

    const saveFilter = (event: object): void => {
        if (!filterName || filterName === '') {
            console.error('Filter name cannot be empty');
            return;
        }

        if (saveFilterHandler) {
            saveFilterHandler(filterName, JSON.stringify(query));
        }
    }

    const updateFilterName = (event: ChangeEvent<HTMLInputElement>) => {
        setFilterName(event.target.value);
    }

    return (
        <Stack spacing={2}>
            <FormControl>
                <TextField label={"Filter name"} variant={"outlined"} onChange={updateFilterName} value={filterName}/>
                <Stack direction={"row"}>
                    <Button variant={"contained"} onClick={saveFilter}>Save</Button>
                    <Button variant={"outlined"}>Clear</Button>
                </Stack>

            </FormControl>
            <QueryBuilder
                fields={fields}
                query={query}
                onQueryChange={setQuery}
            />
            <Container>
                <h2>JSON</h2>
                <pre>{formatQuery(query)}</pre>
                <h2>SQL</h2>
                <pre>{formatQuery(query, "parameterized_named").sql}</pre>
            </Container>
        </Stack>

    );
};
export default Filters;
