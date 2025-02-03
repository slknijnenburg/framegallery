import { Field, formatQuery, QueryBuilder, RuleGroupType } from 'react-querybuilder';
import 'react-querybuilder/dist/query-builder.css';
import React from 'react';
import { ChangeEvent, useEffect, useState } from 'react';
import { Stack } from '@mui/material';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import Button from '@mui/material/Button';
import { Filter } from './Filter';

const fields: Field[] = [
  { name: 'directory', label: 'Directory' },
  { name: 'file_name', label: 'File name' },
  { name: 'aspect_ratio_width', label: 'Aspect ratio width' },
  { name: 'aspect_ratio_height', label: 'Aspect ratio height' },
];

interface FilterBuilderProps {
  selectedFilter?: Filter | undefined;
  saveFilterHandler?: (name: string, rule: string) => void; // eslint-disable-line no-unused-vars, @typescript-eslint/no-unused-vars
  updateFilterHandler?: (id: string, name: string, rule: string) => void; // eslint-disable-line no-unused-vars, @typescript-eslint/no-unused-vars
}

const defaultFilter: RuleGroupType = { id: 'root', combinator: 'and', rules: [] };

const Filters = ({ selectedFilter, saveFilterHandler, updateFilterHandler }: FilterBuilderProps) => {
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

  console.log(query);

  // eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
  const saveFilter = (event: object): void => {
    if (!filterName || filterName === '') {
      console.error('Filter name cannot be empty');
      return;
    }

    if (saveFilterHandler) {
      saveFilterHandler(filterName, JSON.stringify(query));
    }
  };
  // eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
  const updateFilter = (): void => {
    if (!filterName || filterName === '') {
      console.error('Filter name cannot be empty');
      return;
    }

    if (updateFilterHandler && selectedFilter) {
      // @TODO add validation so that filterName must be unique
      updateFilterHandler(selectedFilter.id, filterName, JSON.stringify(query));
    }
  };

  // eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
  const updateFilterName = (event: ChangeEvent<HTMLInputElement>) => {
    setFilterName(event.target.value);
  };
  const removeAllFilters = (): void => {
    setQuery(defaultFilter);
  };

  return (
    <>
      <Stack spacing={2}>
        {/*/!*<FormControl margin={'normal'}>*!/*/}
        {/*/!*    <TextField label={"Filter name"} variant={"outlined"} onChange={updateFilterName} value={filterName}/>*!/*/}
        {/*/!*    <Stack direction={"row"} spacing={2}>*!/*/}
        {/*/!*        <Button variant={"contained"} onClick={saveFilter}>Save as new filter</Button>*!/*/}
        {/*/!*        {selectedFilter && (*!/*/}
        {/*/!*            <Button variant={"contained"} color={"secondary"} onClick={updateFilter}>Update existing filter</Button>*!/*/}
        {/*/!*        )}*!/*/}
        {/*/!*    </Stack>*!/*/}

        {/*</FormControl>*/}
        <Container sx={{ padding: 2 }}>
          <QueryBuilder fields={fields} query={query} onQueryChange={setQuery} />
          <FormControl>
            <Button variant={'outlined'} onClick={removeAllFilters}>
              Clear filters
            </Button>
          </FormControl>
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
