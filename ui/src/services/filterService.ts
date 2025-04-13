import { API_BASE_URL } from '../App';
import { Filter } from '../components/Filters/Filter';

export interface FilterCreate {
  name: string;
  query: string;
}

export interface FilterUpdate {
  name: string;
  query: string;
}

export const filterService = {
  async getFilters() {
    const response = await fetch(`${API_BASE_URL}/api/filters/`);
    if (!response.ok) {
      throw new Error('Failed to fetch filters');
    }
    return response.json();
  },

  async getFilter(id: number) {
    const response = await fetch(`${API_BASE_URL}/api/filters/${id}`);
    if (!response.ok) {
      throw new Error('Failed to fetch filter');
    }
    return response.json();
  },

  async createFilter(filter: FilterCreate): Promise<Filter> {
    const response = await fetch(`${API_BASE_URL}/api/filters/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(filter),
    });
    if (!response.ok) {
      throw new Error('Failed to create filter');
    }
    return response.json();
  },

  async updateFilter(id: number, filter: FilterUpdate): Promise<Filter> {
    const response = await fetch(`${API_BASE_URL}/api/filters/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(filter),
    });
    if (!response.ok) {
      throw new Error('Failed to update filter');
    }
    return response.json();
  },

  async deleteFilter(id: number): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/api/filters/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) {
      throw new Error('Failed to delete filter');
    }
  },
};
