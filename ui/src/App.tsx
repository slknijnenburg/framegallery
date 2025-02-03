import React, { StrictMode, useEffect, useState } from 'react';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import StatusBar, { StatusBarProps } from './components/StatusBar';
import axios from 'axios';
import ImageGrid from './components/ImageGrid';
import Image from './models/Image';
import Filters from './pages/Filters';
import { AppBar, Stack, Toolbar } from '@mui/material';
import { Album, findAlbumById } from './models/Album';
import { RichTreeView, TreeItem2 } from '@mui/x-tree-view';
import { BrowserRouter as Router, Link as RouterLink, Outlet, Route, Routes } from 'react-router-dom';
import Button from '@mui/material/Button';
import { SettingsProvider, useSettings } from './SettingsContext';
import FrameDisplayPreview from './components/FrameDisplayPreview';

export const API_BASE_URL = 'http://localhost:7999';

export default function App() {
  return (
    <StrictMode>
      <SettingsProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Root />}>
              <Route index element={<Home />} />
              <Route path="/browser" element={<Browser />} />
              <Route path="/filters" element={<FiltersOverview />} />
            </Route>
          </Routes>
        </Router>
      </SettingsProvider>
    </StrictMode>
  );
}

function Root() {
  return (
    <>
      <AppBar position="static">
        <Container maxWidth="xl">
          <Toolbar disableGutters>
            <Box sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex' } }}>
              <Button key="home" sx={{ my: 2, color: 'white', display: 'block' }} to="/" component={RouterLink}>
                Home
              </Button>
              <Button
                key="browser"
                sx={{ my: 2, color: 'white', display: 'block' }}
                to="/browser"
                component={RouterLink}
              >
                Browser
              </Button>
              <Button
                key="filters"
                sx={{ my: 2, color: 'white', display: 'block' }}
                to="/filters"
                component={RouterLink}
              >
                Filters
              </Button>
            </Box>
          </Toolbar>
        </Container>
      </AppBar>
      <Outlet />
    </>
  );
}

function Home() {
  const { settings } = useSettings();

  const [status, setStatus] = useState<StatusBarProps>({
    tv_on: false,
    art_mode_supported: false,
    art_mode_active: false,
    api_version: '',
  });
  useEffect(() => {
    const fetchStatus = async () => {
      const url = `${API_BASE_URL}/api/status`;

      try {
        const response = await axios.get(url);
        setStatus(response.data);
      } catch (error) {
        console.error(error);
      }
    };
    fetchStatus();
  }, []); // The empty dependency array ensures the effect runs only once

  return (
    <Stack direction={'column'}>
      <Container maxWidth="xl">
        <Box sx={{ my: 4 }}>
          <Typography variant="h4" sx={{ mb: 2 }} align={'center'}>
            The Frame Art Gallery Manager
          </Typography>
        </Box>
        <Container sx={{ mb: 10 }}>
          <StatusBar
            tv_on={status.tv_on}
            api_version={status.api_version}
            art_mode_active={status.art_mode_active}
            art_mode_supported={status.art_mode_supported}
          />
        </Container>
      </Container>
      <Container>
        <FrameDisplayPreview imageUrl={API_BASE_URL + '/' + settings?.current_active_image.filepath} />
      </Container>
    </Stack>
  );
}

function Browser() {
  const [status, setStatus] = useState<StatusBarProps>({
    tv_on: false,
    art_mode_supported: false,
    art_mode_active: false,
    api_version: '',
  });

  const [items, setItems] = useState<Image[]>([]);
  const [albums, setAlbums] = useState<Album[]>([]);
  const [selectedAlbum, setSelectedAlbum] = useState<Album | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      const url = `${API_BASE_URL}/api/status`;

      try {
        const response = await axios.get(url);
        setStatus(response.data);
      } catch (error) {
        console.error(error);
      }
    };
    fetchStatus();
  }, []); // The empty dependency array ensures the effect runs only once

  useEffect(() => {
    const fetchItems = async () => {
      const url = 'http://localhost:7999/api/available-images';

      try {
        const response = await axios.get(url);
        setItems(response.data);
      } catch (error) {
        console.error(error);
      }
    };
    fetchItems();
  }, []);

  useEffect(() => {
    const fetchItems = async () => {
      const url = 'http://localhost:7999/api/albums';

      try {
        const response = await axios.get(url);
        setAlbums([response.data]);
        setSelectedAlbum(response.data[0]);
      } catch (error) {
        console.error(error);
      }
    };
    fetchItems();
  }, []);

  const selectAlbum = function (event: React.SyntheticEvent, itemIds: string | null): void {
    console.log('Selected album was ', selectedAlbum);
    console.log('New album is ', itemIds);
    console.log(albums);
    // Find the album in the `albums` tree by iterating over each elements `children` property:

    const newAlbum = findAlbumById(albums, itemIds);
    console.log(newAlbum);
    setSelectedAlbum(newAlbum);
  };

  const filteredImages = items.filter((item: Image): boolean => item.filepath.includes(selectedAlbum?.name ?? ''));

  return (
    <Container maxWidth="xl">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" sx={{ mb: 2 }} align={'center'}>
          The Frame Art Gallery Manager
        </Typography>
      </Box>
      <Container sx={{ mb: 10 }}>
        <StatusBar
          tv_on={status.tv_on}
          api_version={status.api_version}
          art_mode_active={status.art_mode_active}
          art_mode_supported={status.art_mode_supported}
        />
      </Container>
      <Stack direction="row" spacing={2} justifyContent="center" alignItems="flex-start">
        <Stack direction="column" spacing={1} justifyContent="flex-start" alignItems="flex-start">
          <Typography variant="h5" component="h2" sx={{ mb: 2 }}>
            Albums
          </Typography>
          <Box sx={{ minWidth: 200 }}>
            <RichTreeView
              items={albums}
              slots={{ item: TreeItem2 }}
              defaultExpandedItems={['/']}
              multiSelect={false}
              onSelectedItemsChange={selectAlbum}
              expansionTrigger={'iconContainer'}
            ></RichTreeView>
          </Box>
        </Stack>
        <Stack direction="column" spacing={1} justifyContent="flex-start" alignItems="flex-start">
          <Typography variant="h5" component="h2" sx={{ mb: 2 }}>
            Photos
          </Typography>
          <ImageGrid items={filteredImages} />
        </Stack>
      </Stack>
    </Container>
  );
}

function FiltersOverview() {
  return <Filters />;
}
