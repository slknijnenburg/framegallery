import React, { useState, useEffect } from 'react';
import ReactCrop, { type PercentCrop, type PixelCrop } from 'react-image-crop';
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



interface CropDialogProps {
  open: boolean;
  image: Image;
  onClose: () => void;
}

const CropDialog: React.FC<CropDialogProps> = ({ open, image, onClose }) => {
  const [crop, setCrop] = useState<[PixelCrop, PercentCrop]>();
  const [completedCrop, setCompletedCrop] = useState<[PixelCrop, PercentCrop]>();

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
  }, [onClose]);

  const handleSaveCrop = async () => {
    const completedPercentCrop = completedCrop?.[1];
    if (completedPercentCrop && image && completedPercentCrop.width && completedPercentCrop.height) {
      const payload = {
        x: completedPercentCrop.x,
        y: completedPercentCrop.y,
        width: completedPercentCrop.width,
        height: completedPercentCrop.height,
      };
      console.log('Saving crop for image ID:', image.id, 'Payload:', payload);

      try {
        const response = await fetch(`${API_BASE_URL}/api/images/${image.id}/crop`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        if (response.ok) {
          const result = await response.json();
          console.log('Crop saved successfully:', result);
          onClose(); // Close dialog on success
        } else {
          const errorResult = await response.json();
          console.error('Failed to save crop:', response.status, errorResult);
          // Optionally, show an error message to the user here
        }
      } catch (error) {
        console.error('Error saving crop:', error);
        // Optionally, show an error message to the user here
      }
    } else {
      console.warn('Cannot save crop: No completed crop, image data, or width/height on crop.');
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
          crop={crop?.[0]}
          onChange={(pixelCrop: PixelCrop, percentageCrop: PercentCrop) => {
            console.log('Changed pixel crop:', pixelCrop)
            console.log('Changed percentage crop:', percentageCrop)
            setCrop([pixelCrop, percentageCrop]);
          }}
          onComplete={(pixelCrop: PixelCrop, percentageCrop: PercentCrop) => {
            console.log('Completed pixel crop:', pixelCrop)
            console.log('Completed percentage crop:', percentageCrop)
            setCompletedCrop([pixelCrop, percentageCrop]);
          }}
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

export default CropDialog;
