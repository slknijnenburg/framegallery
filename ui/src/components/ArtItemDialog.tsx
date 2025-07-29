import * as React from 'react';
import { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import { InputLabel, MenuItem, Select, SelectChangeEvent, Stack, Chip, Box } from '@mui/material';
import Grid from '@mui/material/Grid';
import axios from 'axios';
import Image from '../models/Image';

interface ArtItemDialogProps {
  open: boolean;
  image: Image;
  onClose: () => void;
}

// Create an enum for a set of colors
const MatteColor = {
  black: 'Black',
  neutral: 'Neutral',
  antique: 'Antique',
  warm: 'Warm',
  polar: 'Polar',
  sand: 'Sand',
  seafoam: 'Seafoam',
  sage: 'Sage',
  // It's really burgandy in the settings, not burgundy.
  burgandy: 'Burgandy',
  navy: 'Navy',
  apricot: 'Apricot',
  byzantine: 'Byzantine',
  lavender: 'Lavender',
  redorange: 'Redorange',
  skyblue: 'Skyblue',
  turquoise: 'Turquoise',
};

export default function ArtItemDialog(props: ArtItemDialogProps) {
  const handleClose = () => {
    props.onClose();
  };

  const landscapeMatteStyleSplit = props.image.matte_id?.split('_') ?? ['none', 'black'];
  const landscapeMatteStyle = landscapeMatteStyleSplit[0];
  const landscapeMatteColor = landscapeMatteStyleSplit[1];

  const [matteColor, setMatteColor] = useState<string>(landscapeMatteColor);
  const [matteStyle, setMatteStyle] = useState<string>(landscapeMatteStyle);

  const handleMatteStyleChange = (event: SelectChangeEvent) => {
    setMatteStyle(event.target.value);
  };
  const handleMatteColorChange = (event: SelectChangeEvent) => {
    setMatteColor(event.target.value);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const formJson = Object.fromEntries(formData.entries()) as {
      'art-item-matte-landscape': string;
      'art-item-matte-landscape-color': string;
    };
    let matteId = '';
    if (formJson['art-item-matte-landscape'] === 'none') {
      matteId = 'none';
    } else {
      matteId = `${formJson['art-item-matte-landscape']}_${formJson['art-item-matte-landscape-color']}`;
    }

    // Send the new matte ID to the backend
    try {
      await axios.patch(`/api/available-art/${props.image.id}`, {
        matte_id: matteId,
        portrait_matte_id: matteId,
      });
    } catch (error) {
      console.error(error);
    }

    handleClose();
  };

  return (
    <Dialog
      open={props.open}
      onClose={handleClose}
      PaperProps={{
        component: 'form',
        onSubmit: handleSubmit,
      }}
    >
      <DialogTitle>Item properties for {props.image.filename}</DialogTitle>
      <DialogContent>
        <DialogContentText>Update the display settings for the art item here.</DialogContentText>
        <Stack direction="column">
          <Grid container justifyContent="space-between" alignItems="center">
            <Grid size={4} sx={{ mb: 2 }}>
              <InputLabel id="art-item-matte-landscape-label">Matte style:</InputLabel>
            </Grid>
            <Grid size={8} alignItems="right" alignContent="right" sx={{ textAlign: 'right', mb: 2 }}>
              <Select
                labelId="art-item-matte-landscape-label"
                id="art-item-matte-landscape"
                name="art-item-matte-landscape"
                value={matteStyle}
                label="Matte (Landscape)"
                onChange={handleMatteStyleChange}
                variant="outlined"
                sx={{ width: '100%' }}
              >
                <MenuItem value="shadowbox">Shadowbox</MenuItem>
                <MenuItem value="flexible">Flexible</MenuItem>
                <MenuItem value="none">None</MenuItem>
              </Select>
            </Grid>

            <Grid size={4} sx={{ mb: 2 }}>
              <InputLabel id="art-item-matte-landscape-color-label">Matte color:</InputLabel>
            </Grid>
            <Grid size={8} sx={{ textAlign: 'right', mb: 2 }}>
              <Select
                labelId="art-item-matte-landscape-color-label"
                id="art-item-matte-landscape-color"
                name="art-item-matte-landscape-color"
                value={matteColor}
                label="Matte color"
                onChange={handleMatteColorChange}
                variant="outlined"
                sx={{ width: '100%' }}
              >
                {Object.entries(MatteColor).map(([value, description]) => (
                  <MenuItem key={value} value={value}>
                    {description}
                  </MenuItem>
                ))}
              </Select>
            </Grid>

            {/* Keywords section */}
            <Grid size={4} sx={{ mb: 2 }}>
              <InputLabel>Keywords:</InputLabel>
            </Grid>
            <Grid size={8} sx={{ textAlign: 'right', mb: 2 }}>
              {props.image.keywords && props.image.keywords.length > 0 ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, justifyContent: 'flex-end' }}>
                  {props.image.keywords.map((keyword, index) => (
                    <Chip key={index} label={keyword} size="small" variant="outlined" />
                  ))}
                </Box>
              ) : (
                <Box sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                  No keywords found
                </Box>
              )}
            </Grid>
          </Grid>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button type="submit">Submit</Button>
      </DialogActions>
    </Dialog>
  );
}
