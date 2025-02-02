import axios from 'axios';
import { API_BASE_URL } from '../App';

export const enableSlideshow = async () => {
  try {
    console.log('Enabling slideshow via API');
    await axios.post(`${API_BASE_URL}/api/slideshow/enable`);
  } catch (error) {
    console.error(error);
  }
};

export const disableSlideshow = async () => {
  try {
    console.log('Disabling slideshow via API');
    await axios.post(`${API_BASE_URL}/api/slideshow/disable`);
  } catch (error) {
    console.error(error);
  }
};
