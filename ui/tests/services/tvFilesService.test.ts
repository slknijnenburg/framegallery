import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { tvFilesService, TvServiceError } from '../../src/services/tvFilesService';
import { TV_CATEGORIES } from '../../src/models/TvFile';

// Mock fetch globally
const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
global.fetch = mockFetch;

describe('tvFilesService', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('getTvFiles', () => {
    it('should fetch TV files successfully', async () => {
      const mockFiles = [
        {
          content_id: 'MY-F0001',
          file_name: 'Test Photo',
          file_type: 'JPEG',
          file_size: 1024576,
          date: '2024-01-15',
          category_id: 'MY-C0002',
          thumbnail_available: true,
          matte: 'none',
        },
      ];

      const mockResponse = {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: jest.fn().mockResolvedValue(mockFiles),
      };
      mockFetch.mockResolvedValue(mockResponse as Response);

      const result = await tvFilesService.getTvFiles();

      expect(result).toEqual(mockFiles);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tv/files?category=MY-C0002')
      );
    });

    it('should handle custom category parameter', async () => {
      const mockFiles = [];

      const mockResponse = {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: jest.fn().mockResolvedValue(mockFiles),
      };
      mockFetch.mockResolvedValue(mockResponse as Response);

      await tvFilesService.getTvFiles(TV_CATEGORIES.ART_STORE);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tv/files?category=MY-C0001')
      );
    });

    it('should throw TvServiceError for 503 status (TV unavailable)', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        json: jest.fn(),
      } as Response);

      await expect(tvFilesService.getTvFiles()).rejects.toThrow(TvServiceError);

      try {
        await tvFilesService.getTvFiles();
      } catch (error) {
        expect(error).toBeInstanceOf(TvServiceError);
        if (error instanceof TvServiceError) {
          expect(error.status).toBe(503);
          expect(error.isServiceUnavailable).toBe(true);
          expect(error.message).toContain('TV is not connected');
        }
      }
    });

    it('should throw TvServiceError for 500 status (server error)', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: jest.fn(),
      } as Response);

      await expect(tvFilesService.getTvFiles()).rejects.toThrow(TvServiceError);

      try {
        await tvFilesService.getTvFiles();
      } catch (error) {
        expect(error).toBeInstanceOf(TvServiceError);
        if (error instanceof TvServiceError) {
          expect(error.status).toBe(500);
          expect(error.isServiceUnavailable).toBe(false);
          expect(error.message).toContain('Server error');
        }
      }
    });

    it('should throw TvServiceError for other HTTP errors', async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: jest.fn(),
      } as Response);

      await expect(tvFilesService.getTvFiles()).rejects.toThrow(TvServiceError);

      try {
        await tvFilesService.getTvFiles();
      } catch (error) {
        expect(error).toBeInstanceOf(TvServiceError);
        if (error instanceof TvServiceError) {
          expect(error.status).toBe(404);
          expect(error.message).toContain('Not Found');
        }
      }
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValue(new TypeError('fetch failed'));

      await expect(tvFilesService.getTvFiles()).rejects.toThrow(TvServiceError);

      try {
        await tvFilesService.getTvFiles();
      } catch (error) {
        expect(error).toBeInstanceOf(TvServiceError);
        if (error instanceof TvServiceError) {
          expect(error.message).toContain('Network error');
        }
      }
    });

    it('should handle unexpected errors', async () => {
      mockFetch.mockRejectedValue(new Error('Unexpected error'));

      await expect(tvFilesService.getTvFiles()).rejects.toThrow(TvServiceError);

      try {
        await tvFilesService.getTvFiles();
      } catch (error) {
        expect(error).toBeInstanceOf(TvServiceError);
        if (error instanceof TvServiceError) {
          expect(error.message).toContain('Unexpected error');
        }
      }
    });
  });

  describe('getAvailableCategories', () => {
    it('should return available categories', () => {
      const categories = tvFilesService.getAvailableCategories();

      expect(categories).toHaveLength(2);
      expect(categories[0]).toEqual({ id: 'MY-C0002', name: 'User Content' });
      expect(categories[1]).toEqual({ id: 'MY-C0001', name: 'Art Store' });
    });
  });

  describe('formatFileSize', () => {
    it('should format bytes correctly', () => {
      expect(tvFilesService.formatFileSize(0)).toBe('0 B');
      expect(tvFilesService.formatFileSize(512)).toBe('512 B');
      expect(tvFilesService.formatFileSize(1024)).toBe('1.0 KB');
      expect(tvFilesService.formatFileSize(1048576)).toBe('1.0 MB');
      expect(tvFilesService.formatFileSize(1073741824)).toBe('1.0 GB');
      expect(tvFilesService.formatFileSize(1536)).toBe('1.5 KB');
    });

    it('should handle null values', () => {
      expect(tvFilesService.formatFileSize(null)).toBe('Unknown');
      expect(tvFilesService.formatFileSize(undefined as unknown as number | null)).toBe('Unknown');
    });

    it('should handle very large files', () => {
      expect(tvFilesService.formatFileSize(5 * 1024 * 1024 * 1024)).toBe('5.0 GB');
    });
  });

  describe('formatDate', () => {
    it('should format valid dates', () => {
      const result = tvFilesService.formatDate('2024-01-15');
      // Note: The exact format depends on the user's locale, but it should contain the date parts
      expect(result).toMatch(/2024/);
      expect(result).toMatch(/Jan|15/);
    });

    it('should handle null dates', () => {
      expect(tvFilesService.formatDate(null)).toBe('Unknown');
    });

    it('should handle invalid dates', () => {
      expect(tvFilesService.formatDate('invalid-date')).toBe('Invalid Date');
    });

    it('should handle empty strings', () => {
      expect(tvFilesService.formatDate('')).toBe('Unknown');
    });
  });

  describe('request URLs', () => {
    /**
     * These pin the fix for "URL constructor: is not a valid URL".
     *
     * The service used to build requests with `new URL(path, base)`, where base was
     * API_BASE_URL ('') anywhere other than localhost. An empty string is not a valid
     * base URL, so the constructor threw before any request was made -- meaning the
     * TV Files page failed for every real deployment while working on a dev machine.
     */
    const okResponse = () =>
      ({ ok: true, status: 200, statusText: 'OK', json: jest.fn().mockResolvedValue([]) }) as unknown as Response;

    it('requests a relative path rather than a hardcoded origin', async () => {
      mockFetch.mockResolvedValue(okResponse());

      await tvFilesService.getTvFiles();

      const requested = mockFetch.mock.calls[0][0] as string;
      expect(requested.startsWith('/api/tv/files')).toBe(true);
      expect(requested).not.toContain('localhost');
      expect(requested).not.toContain('http');
    });

    it('encodes the category as a query parameter', async () => {
      mockFetch.mockResolvedValue(okResponse());

      await tvFilesService.getTvFiles(TV_CATEGORIES.ART_STORE);

      expect(mockFetch.mock.calls[0][0]).toBe('/api/tv/files?category=MY-C0001');
    });

    it('builds relative paths for the delete endpoints too', async () => {
      mockFetch.mockResolvedValue({ ok: true, status: 204, statusText: 'No Content' } as Response);
      await tvFilesService.deleteTvFile('MY-F0001');
      expect(mockFetch.mock.calls[0][0]).toBe('/api/tv/files/MY-F0001');

      mockFetch.mockReset();
      mockFetch.mockResolvedValue(okResponse());
      await tvFilesService.deleteTvFiles(['MY-F0001']);
      expect(mockFetch.mock.calls[0][0]).toBe('/api/tv/files/delete');
    });
  });
});
