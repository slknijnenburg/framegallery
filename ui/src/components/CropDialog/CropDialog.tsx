import React, { useState, useRef, useEffect } from 'react';
import ReactCrop, { type Crop, centerCrop, makeAspectCrop } from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';
import './CropDialog.css';
import Image from '../../models/Image';
import { API_BASE_URL } from '../../App';
import Button from '@mui/material/Button';
import { Dialog, DialogActions, DialogTitle } from '@mui/material';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';

// Define the fixed aspect ratio
const FIXED_ASPECT_RATIO = 16 / 9;

function centerAspectCrop(
  mediaWidth: number,
  mediaHeight: number,
  aspect: number,
): Crop {
  return centerCrop(
    makeAspectCrop(
      {
        unit: '%',
        width: 90,
      },
      aspect,
      mediaWidth,
      mediaHeight,
    ),
    mediaWidth,
    mediaHeight,
  );
}

interface CropDialog2Props {
  open: boolean;
  image: Image;
  onClose: () => void;
}

const CropDialog2: React.FC<CropDialog2Props> = ({ open, image, onClose }) => {
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<Crop>();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleSaveCrop = () => {
    if (completedCrop && image) {
      console.log('Saving crop for image ID:', image.id, 'Crop data (percentage):', completedCrop);
      onClose();
    } else {
      console.warn('Cannot save crop: No completed crop or image data.');
    }
  };

  const handleCancel = () => {
    onClose();
  };

  return (
    <Dialog
      fullWidth={true}
      maxWidth="xl"
      open={open}
      onClose={handleCancel}
    >
      <DialogTitle>Crop Image</DialogTitle>
      <DialogContent>
        <DialogContentText>Select a 16:9 crop for the image</DialogContentText>
        <ReactCrop 
          crop={crop}
          onChange={setCrop}
          aspect={FIXED_ASPECT_RATIO}>
            <img src={`${API_BASE_URL}/${image.filepath}`} />
          </ReactCrop>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCancel}>Cancel</Button>
        <Button variant="contained" onClick={handleSaveCrop}>Save</Button>
      </DialogActions>
    </Dialog>
  );
};

export default CropDialog2; 