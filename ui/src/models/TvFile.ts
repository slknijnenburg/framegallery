/**
 * TypeScript interface for TV file information from Samsung Frame TV.
 * Matches the TvFileResponse schema from the backend.
 */
export interface TvFile {
  /** Unique identifier from TV */
  content_id: string;
  /** Display name of the file */
  file_name: string;
  /** File format (JPEG, PNG, etc.) */
  file_type: string;
  /** File size in bytes */
  file_size: number | null;
  /** Upload/creation date */
  date: string | null;
  /** TV category identifier */
  category_id: string;
  /** Whether thumbnail exists */
  thumbnail_available: boolean | null;
  /** Applied matte style */
  matte: string | null;
}

/**
 * Available TV categories for filtering files.
 */
export const TV_CATEGORIES = {
  USER_CONTENT: 'MY-C0002',
  ART_STORE: 'MY-C0001',
} as const;

export type TvCategory = typeof TV_CATEGORIES[keyof typeof TV_CATEGORIES];

/**
 * Category display names for UI.
 */
export const TV_CATEGORY_NAMES: Record<TvCategory, string> = {
  [TV_CATEGORIES.USER_CONTENT]: 'User Content',
  [TV_CATEGORIES.ART_STORE]: 'Art Store',
};
