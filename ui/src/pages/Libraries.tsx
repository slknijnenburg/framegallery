import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  OutlinedInput,
  Select,
  SelectChangeEvent,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { libraryService } from '../services/libraryService';
import { ImmichAlbum, LibraryStatus, LibrarySummary } from '../models/Library';

interface ImmichFormState {
  id: number | null;
  name: string;
  baseUrl: string;
  apiKey: string;
  albumIds: string[];
}

const emptyForm: ImmichFormState = { id: null, name: '', baseUrl: '', apiKey: '', albumIds: [] };

const Libraries = () => {
  const [libraries, setLibraries] = useState<LibrarySummary[]>([]);
  const [statuses, setStatuses] = useState<Record<string, LibraryStatus>>({});
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<ImmichFormState>(emptyForm);
  const [albums, setAlbums] = useState<ImmichAlbum[]>([]);
  const [testStatus, setTestStatus] = useState<string>('');
  const [testing, setTesting] = useState(false);

  const loadStatus = async () => {
    // Best-effort: live counts hit the external servers, so don't fail the page if they error.
    try {
      const list = await libraryService.getStatus();
      setStatuses(Object.fromEntries(list.map((s) => [s.library_id, s])));
    } catch {
      setStatuses({});
    } finally {
      setStatusLoaded(true);
    }
  };

  const loadLibraries = async () => {
    try {
      setLibraries(await libraryService.getLibraries());
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load libraries');
    } finally {
      setLoading(false);
    }
    await loadStatus();
  };

  useEffect(() => {
    // Load once on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadLibraries();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openAddDialog = () => {
    setForm(emptyForm);
    setAlbums([]);
    setTestStatus('');
    setDialogOpen(true);
  };

  const openEditDialog = async (library: LibrarySummary) => {
    setForm({
      id: library.id,
      name: library.name,
      baseUrl: library.base_url ?? '',
      apiKey: '',
      albumIds: library.album_ids,
    });
    setAlbums([]);
    setDialogOpen(true);
    // Load albums using the stored API key so it needn't be re-entered to change the selection.
    if (library.has_api_key) {
      setTestStatus('Loading albums…');
      try {
        setAlbums(await libraryService.getStoredAlbums(library.id));
        setTestStatus('Using the saved API key — leave the key field blank to keep it.');
      } catch (err) {
        setTestStatus(err instanceof Error ? err.message : 'Failed to load albums');
      }
    } else {
      setTestStatus('');
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestStatus('');
    // When editing without a new key, reuse the library's stored credentials.
    const useStored = form.id !== null && form.apiKey === '';
    try {
      const result = useStored
        ? await libraryService.testStoredConnection(form.id as number)
        : await libraryService.testConnection(form.baseUrl, form.apiKey);
      if (result.ok) {
        setTestStatus(`Connected${result.version ? ` (Immich ${result.version})` : ''}. Loading albums…`);
        const albumList = useStored
          ? await libraryService.getStoredAlbums(form.id as number)
          : await libraryService.getAlbums(form.baseUrl, form.apiKey);
        setAlbums(albumList);
        setTestStatus(`Connected${result.version ? ` (Immich ${result.version})` : ''}.`);
      } else {
        setTestStatus(`Connection failed: ${result.error ?? 'unknown error'}`);
      }
    } catch (err) {
      setTestStatus(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setTesting(false);
    }
  };

  const handleAlbumsChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setForm({ ...form, albumIds: typeof value === 'string' ? value.split(',') : value });
  };

  const handleSave = async () => {
    try {
      if (form.id === null) {
        await libraryService.createLibrary({
          name: form.name,
          source_type: 'immich',
          base_url: form.baseUrl,
          api_key: form.apiKey,
          album_ids: form.albumIds,
        });
      } else {
        await libraryService.updateLibrary(form.id, {
          name: form.name,
          base_url: form.baseUrl,
          // Only send the key when the user entered a new one.
          ...(form.apiKey ? { api_key: form.apiKey } : {}),
          album_ids: form.albumIds,
        });
      }
      setDialogOpen(false);
      await loadLibraries();
    } catch (err) {
      setTestStatus(err instanceof Error ? err.message : 'Failed to save library');
    }
  };

  const handleToggleEnabled = async (library: LibrarySummary) => {
    await libraryService.updateLibrary(library.id, { enabled: !library.enabled });
    await loadLibraries();
  };

  const handleWeightChange = async (library: LibrarySummary, weight: number) => {
    if (!Number.isNaN(weight) && weight !== library.weight) {
      await libraryService.updateLibrary(library.id, { weight });
      await loadLibraries();
    }
  };

  const handleDelete = async (library: LibrarySummary) => {
    await libraryService.deleteLibrary(library.id);
    await loadLibraries();
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  const enabledLibraries = libraries.filter((library) => library.enabled);
  const anyPhotosAvailable = enabledLibraries.some((library) => (statuses[library.library_id]?.count ?? 0) > 0);
  const showNoPhotosWarning = statusLoaded && !anyPhotosAvailable;

  const renderStatusChip = (library: LibrarySummary) => {
    const libraryStatus = statuses[library.library_id];
    if (!statusLoaded || !libraryStatus) {
      return <Chip size="small" label="checking…" />;
    }
    if (libraryStatus.error) {
      return <Chip size="small" color="error" label={`Unavailable: ${libraryStatus.error}`} />;
    }
    const count = libraryStatus.count ?? 0;
    if (count === 0) {
      return <Chip size="small" color="warning" label="0 matching photos" />;
    }
    return <Chip size="small" color="success" label={`${count} photos`} />;
  };

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', mt: 4, px: 2 }}>
      <Stack direction="row" sx={{ justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h4">Libraries</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openAddDialog}>
          Add Immich Library
        </Button>
      </Stack>
      <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
        The slideshow blends photos across all enabled libraries, weighted by the number of matching photos in each.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {showNoPhotosWarning && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {enabledLibraries.length === 0
            ? 'No libraries are enabled, so the slideshow has nothing to display.'
            : 'No photos are available from any enabled library — the slideshow cannot display anything. '
              + 'Check the per-library status below (e.g. an unreachable server or an empty album selection).'}
        </Alert>
      )}

      <Stack spacing={2}>
        {libraries.map((library) => (
          <Card key={library.id} variant="outlined">
            <CardHeader
              title={library.name}
              subheader={library.is_local ? 'Local gallery' : `Immich · ${library.base_url ?? ''}`}
              action={
                <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                  <FormControlLabel
                    control={<Switch checked={library.enabled} onChange={() => handleToggleEnabled(library)} />}
                    label="Enabled"
                  />
                  {!library.is_local && (
                    <>
                      <IconButton aria-label="Edit library" onClick={() => openEditDialog(library)}>
                        <EditIcon />
                      </IconButton>
                      <IconButton aria-label="Delete library" onClick={() => handleDelete(library)}>
                        <DeleteIcon />
                      </IconButton>
                    </>
                  )}
                </Stack>
              }
            />
            <CardContent>
              <Stack direction="row" spacing={2} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
                {renderStatusChip(library)}
                <TextField
                  // Remount when the saved weight changes so the uncontrolled input doesn't show a stale value.
                  key={`weight-${library.id}-${library.weight}`}
                  label="Weight"
                  type="number"
                  size="small"
                  defaultValue={library.weight}
                  onBlur={(e) => handleWeightChange(library, parseFloat(e.target.value))}
                  sx={{ width: 110 }}
                  slotProps={{ htmlInput: { step: 0.1, min: 0 } }}
                />
                {library.is_local ? (
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    Selection is controlled by the active{' '}
                    <RouterLink to="/filters">filter</RouterLink>.
                  </Typography>
                ) : (
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    {library.album_ids.length} album{library.album_ids.length === 1 ? '' : 's'} selected
                  </Typography>
                )}
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{form.id === null ? 'Add Immich Library' : 'Edit Immich Library'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Immich base URL"
              placeholder="http://immich.local:2283"
              value={form.baseUrl}
              onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
              fullWidth
            />
            <TextField
              label="API key"
              type="password"
              value={form.apiKey}
              onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
              helperText={form.id !== null ? 'Leave blank to keep the saved API key' : ''}
              fullWidth
            />
            <Button
              variant="outlined"
              onClick={handleTestConnection}
              // A new library needs a key; when editing, the stored key is reused if this is blank.
              disabled={testing || !form.baseUrl || (form.id === null && !form.apiKey)}
            >
              {testing ? 'Testing…' : 'Test connection & load albums'}
            </Button>
            {testStatus && <Alert severity={testStatus.startsWith('Connected') ? 'success' : 'info'}>{testStatus}</Alert>}
            {albums.length > 0 && (
              <Box>
                <InputLabel id="album-select-label">Albums</InputLabel>
                <Select
                  labelId="album-select-label"
                  multiple
                  fullWidth
                  value={form.albumIds}
                  onChange={handleAlbumsChange}
                  input={<OutlinedInput />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((id) => (
                        <Chip key={id} label={albums.find((a) => a.id === id)?.name ?? id} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {albums.map((album) => (
                    <MenuItem key={album.id} value={album.id}>
                      {album.name}
                      {album.photo_count != null ? ` (${album.photo_count})` : ''}
                    </MenuItem>
                  ))}
                </Select>
              </Box>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={!form.name || !form.baseUrl}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Libraries;
