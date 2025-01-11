import { InputLabel, MenuItem, Select, SelectChangeEvent } from "@mui/material";
import Container from "@mui/material/Container";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid2";
import React, { ReactNode, useState } from "react";
import FilterBuilder from "../components/Filters/FilterBuilder";
import { Filter } from "../components/Filters/Filter";

const testFilters = [
    {
        id: '1',
        name: '16:9 aspect ratio',
        query: '{"id":"root","combinator":"and","rules":[{"id":"b06c8a69-747e-4e37-acb0-e8e9210e801e","field":"aspect_ratio_width","operator":"=","valueSource":"value","value":"16"},{"id":"d7360b89-0cac-4f23-bd2c-318778f08e09","field":"aspect_ratio_height","operator":"=","valueSource":"value","value":"9"}]}'
    },
    {id: '2', name: 'Holiday photos'},
    {id: '3', name: 'Wedding'}
];

const Filters = () => {
    const [filters, setFilters] = useState<Filter[]>([]);
    const [selectedFilter, setSelectedFilter] = useState<Filter>();

    const handleFilterChange = (event: SelectChangeEvent<string>, child?: ReactNode) => {
        const filterId = event.target.value;
        const filter = filters.find((filter) => filter.id === filterId);
        if (filter) {
            console.log('Filter changed to:', filter);
            setSelectedFilter(filter);
        }
    };

    // TODO add support to delete filters
    const handleSaveFilter = (name: string, rule: string) => {
        // TODO add support to update existing filters
        const newFilter = {
            id: (filters.length + 1).toString(),
            name: name,
            query: rule
        };
        setFilters([...filters, newFilter]);
        setSelectedFilter(newFilter);
    }

    const handleUpdateFilter = (id: string, name: string, rule: string) => {
        const updatedFilters = filters.map((filter) =>
            filter.id === id ? {...filter, name, query: rule} : filter
        );
        setFilters(updatedFilters);
        const updatedFilter = updatedFilters.find((filter) => filter.id === id);
        setSelectedFilter(updatedFilter);
    };

    return (
        <Container maxWidth="xl">
            <Grid container spacing={2}>
                <Grid size={6}>
                    <h1>Filters</h1>
                </Grid>
                <Grid size={12}>
                    <FormControl fullWidth>
                        <InputLabel id="filter-select-label">Filter</InputLabel>
                        <Select
                            labelId="filter-select-label"
                            id="filter-select"
                            label="Filter"
                            value={selectedFilter?.id || filters[0]?.id || ''}
                            onChange={handleFilterChange}
                        >
                            {
                                filters.map((filter) => (
                                    <MenuItem key={filter.id} value={filter.id}>{filter.name}</MenuItem>
                                ))
                            }
                        </Select>
                    </FormControl>
                </Grid>
                <Grid size={12}/>
            </Grid>
            <FilterBuilder
                selectedFilter={selectedFilter}
                saveFilterHandler={handleSaveFilter}
                updateFilterHandler={handleUpdateFilter}
            />
        </Container>
    );
}

export default Filters;