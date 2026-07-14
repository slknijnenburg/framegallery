/** A configured photo library as returned by the backend (never includes the API key). */
export interface LibrarySummary {
  id: number;
  library_id: string;
  name: string;
  source_type: string;
  enabled: boolean;
  weight: number;
  is_local: boolean;
  has_api_key: boolean;
  base_url?: string | null;
  album_ids: string[];
  filter_id?: number | null;
}

export interface LibraryCreate {
  name: string;
  source_type: 'immich';
  base_url: string;
  api_key: string;
  album_ids: string[];
  enabled?: boolean;
  weight?: number;
}

export interface LibraryUpdate {
  name?: string;
  enabled?: boolean;
  weight?: number;
  base_url?: string;
  api_key?: string;
  album_ids?: string[];
  filter_id?: number | null;
}

export interface LibraryStatus {
  id: number;
  library_id: string;
  enabled: boolean;
  count?: number | null;
  error?: string | null;
}

export interface ImmichAlbum {
  id: string;
  name: string;
  photo_count?: number | null;
}

export interface ConnectionTestResult {
  ok: boolean;
  version?: string | null;
  error?: string | null;
}
