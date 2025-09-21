import { API_BASE_URL } from '../App';
import { TvFile, TvCategory, TV_CATEGORIES } from '../models/TvFile';

// Helper function to detect development mode
const isDevelopmentMode = () => {
  // Check for Jest environment (when window might not exist)
  if (typeof window === 'undefined') {
    return false;
  }

  // Check hostname for development - covers both Vite dev server and general localhost usage
  return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
};

/**
 * Error class for TV-specific errors.
 */
export class TvServiceError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly isServiceUnavailable: boolean = false
  ) {
    super(message);
    this.name = 'TvServiceError';
  }
}

/**
 * Service for interacting with TV files API.
 */
export const tvFilesService = {
  /**
   * Fetch files from the Samsung Frame TV.
   *
   * @param category - TV category to filter files (defaults to user content)
   * @returns Promise<TvFile[]> - Array of TV files
   * @throws TvServiceError - When TV is unavailable or other errors occur
   */
  async getTvFiles(category: TvCategory = TV_CATEGORIES.USER_CONTENT): Promise<TvFile[]> {
    try {
      // Use direct backend URL in development, relative URL in production
      const isDevelopment = isDevelopmentMode();
      const baseUrl = isDevelopment ? 'http://localhost:7999' : API_BASE_URL;
      const url = new URL('/api/tv/files', baseUrl);
      url.searchParams.set('category', category);

      const response = await fetch(url.toString());

      if (!response.ok) {
        // Handle specific error cases
        if (response.status === 503) {
          throw new TvServiceError(
            'TV is not connected or unavailable. Please check your TV connection.',
            503,
            true
          );
        }

        if (response.status >= 500) {
          throw new TvServiceError(
            'Server error while retrieving TV files. Please try again later.',
            response.status
          );
        }

        throw new TvServiceError(
          `Failed to fetch TV files: ${response.statusText}`,
          response.status
        );
      }

      const files: TvFile[] = await response.json();
      return files;

    } catch (error) {
      // Re-throw TvServiceError as-is
      if (error instanceof TvServiceError) {
        throw error;
      }

      // Handle network/fetch errors
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new TvServiceError(
          'Network error: Unable to connect to the server. Please check your connection.',
          0
        );
      }

      // Handle other unexpected errors
      throw new TvServiceError(
        `Unexpected error while fetching TV files: ${error instanceof Error ? error.message : 'Unknown error'}`,
        0
      );
    }
  },

  /**
   * Get available TV categories.
   *
   * @returns Array of category objects with id and display name
   */
  getAvailableCategories(): Array<{ id: TvCategory; name: string }> {
    return [
      { id: TV_CATEGORIES.USER_CONTENT, name: 'User Content' },
      { id: TV_CATEGORIES.ART_STORE, name: 'Art Store' },
    ];
  },

  /**
   * Format file size for display.
   *
   * @param bytes - File size in bytes
   * @returns Formatted file size string
   */
  formatFileSize(bytes: number | null): string {
    if (bytes === null || bytes === undefined) {
      return 'Unknown';
    }

    if (bytes === 0) {
      return '0 B';
    }

    const units = ['B', 'KB', 'MB', 'GB'];
    const base = 1024;
    const digitGroups = Math.floor(Math.log(bytes) / Math.log(base));
    const unitIndex = Math.min(digitGroups, units.length - 1);

    const size = bytes / Math.pow(base, unitIndex);
    const formattedSize = unitIndex === 0 ? size.toString() : size.toFixed(1);

    return `${formattedSize} ${units[unitIndex]}`;
  },

  /**
   * Format date for display.
   *
   * @param dateString - ISO date string
   * @returns Formatted date string
   */
  formatDate(dateString: string | null): string {
    if (!dateString) {
      return 'Unknown';
    }

    try {
      const date = new Date(dateString);
      return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'Invalid Date';
    }
  },
};
