import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { tvFilesService, TvServiceError } from '../../src/services/tvFilesService';
import { TV_CATEGORIES } from '../../src/models/TvFile';

// Mock fetch globally
const mockFetch = jest.fn() as jest.MockedFunction<typeof fetch>;
global.fetch = mockFetch;

describe('tvFilesService', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('getTvFiles', () => {
    it.skip('should fetch TV files successfully', async () => {
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
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      const result = await tvFilesService.getTvFiles();

      expect(result).toEqual(mockFiles);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tv/files?category=MY-C0002')
      );
    });

    it.skip('should handle custom category parameter', async () => {
      const mockFiles = [];

      const mockResponse = {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: jest.fn().mockResolvedValue(mockFiles),
      };
      mockFetch.mockResolvedValueOnce(mockResponse as Response);

      await tvFilesService.getTvFiles(TV_CATEGORIES.ART_STORE);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tv/files?category=MY-C0001')
      );
    });

    it.skip('should throw TvServiceError for 503 status (TV unavailable)', async () => {
      mockFetch.mockResolvedValueOnce({
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

    it.skip('should throw TvServiceError for 500 status (server error)', async () => {
      mockFetch.mockResolvedValueOnce({
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

    it.skip('should throw TvServiceError for other HTTP errors', async () => {
      mockFetch.mockResolvedValueOnce({
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

    it.skip('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('fetch failed'));

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

    it.skip('should handle unexpected errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Unexpected error'));

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

    it.skip('should handle null values', () => {
      expect(tvFilesService.formatFileSize(null)).toBe('Unknown');
      expect(tvFilesService.formatFileSize(undefined as unknown as number | null)).toBe('Unknown');
    });

    it.skip('should handle very large files', () => {
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

    it.skip('should handle null dates', () => {
      expect(tvFilesService.formatDate(null)).toBe('Unknown');
    });

    it.skip('should handle invalid dates', () => {
      expect(tvFilesService.formatDate('invalid-date')).toBe('Invalid Date');
    });

    it.skip('should handle empty strings', () => {
      expect(tvFilesService.formatDate('')).toBe('Unknown');
    });
  });
});
