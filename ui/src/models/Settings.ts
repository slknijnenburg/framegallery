import { Filter } from '../components/Filters/Filter';
import ActivePhoto from './Photo';

export interface Settings {
  slideshow_enabled: boolean;
  slideshow_interval: number;
  current_active_photo: ActivePhoto | null;
  current_active_image_since: string | null;
  active_filter: Filter | null;
  auto_cleanup_enabled: boolean;
  /** While true the app pushes no images and never restores art mode. */
  tv_watch_mode_enabled: boolean;
}
