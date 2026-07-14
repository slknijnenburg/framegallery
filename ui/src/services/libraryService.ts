import { API_BASE_URL } from '../App';
import {
  ConnectionTestResult,
  ImmichAlbum,
  LibraryCreate,
  LibraryStatus,
  LibrarySummary,
  LibraryUpdate,
} from '../models/Library';

const jsonHeaders = { 'Content-Type': 'application/json' };

export const libraryService = {
  async getLibraries(): Promise<LibrarySummary[]> {
    const response = await fetch(`${API_BASE_URL}/api/libraries`);
    if (!response.ok) {
      throw new Error('Failed to fetch libraries');
    }
    return response.json();
  },

  async getStatus(): Promise<LibraryStatus[]> {
    const response = await fetch(`${API_BASE_URL}/api/libraries/status`);
    if (!response.ok) {
      throw new Error('Failed to fetch library status');
    }
    return response.json();
  },

  async createLibrary(payload: LibraryCreate): Promise<LibrarySummary> {
    const response = await fetch(`${API_BASE_URL}/api/libraries`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error('Failed to create library');
    }
    return response.json();
  },

  async updateLibrary(id: number, payload: LibraryUpdate): Promise<LibrarySummary> {
    const response = await fetch(`${API_BASE_URL}/api/libraries/${id}`, {
      method: 'PUT',
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error('Failed to update library');
    }
    return response.json();
  },

  async deleteLibrary(id: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/libraries/${id}`, { method: 'DELETE' });
    if (!response.ok) {
      throw new Error('Failed to delete library');
    }
  },

  async testConnection(base_url: string, api_key: string): Promise<ConnectionTestResult> {
    const response = await fetch(`${API_BASE_URL}/api/libraries/test-connection`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ base_url, api_key }),
    });
    if (!response.ok) {
      throw new Error('Failed to test connection');
    }
    return response.json();
  },

  async getAlbums(base_url: string, api_key: string): Promise<ImmichAlbum[]> {
    const response = await fetch(`${API_BASE_URL}/api/libraries/albums`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ base_url, api_key }),
    });
    if (!response.ok) {
      throw new Error('Failed to fetch albums');
    }
    return response.json();
  },

  // The following two use the library's stored API key, so it needn't be re-entered to edit albums.
  async testStoredConnection(id: number): Promise<ConnectionTestResult> {
    const response = await fetch(`${API_BASE_URL}/api/libraries/${id}/test-connection`, { method: 'POST' });
    if (!response.ok) {
      throw new Error('Failed to test connection');
    }
    return response.json();
  },

  async getStoredAlbums(id: number): Promise<ImmichAlbum[]> {
    const response = await fetch(`${API_BASE_URL}/api/libraries/${id}/albums`);
    if (!response.ok) {
      throw new Error('Failed to fetch albums');
    }
    return response.json();
  },
};
