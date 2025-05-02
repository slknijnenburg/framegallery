import { Filter } from '../components/Filters/Filter';
import Image from './Image';

export interface Settings {
  slideshow_enabled: boolean;
  slideshow_interval: number;
  current_active_image: Image;
  current_active_image_since: string | null;
  active_filter: Filter | null;
}
