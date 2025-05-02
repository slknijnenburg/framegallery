import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { API_BASE_URL } from './App';
import Image from './models/Image';

// Define the shape of your settings
import { Filter } from './components/Filters/Filter';

interface Settings {
  slideshow_enabled: boolean;
  slideshow_interval: number;
  current_active_image: Image;
  current_active_image_since: string | null;
  active_filter: Filter | null;
}

// Define the context value type
interface SettingsContextValue {
  settings: Settings | null;
  loading: boolean;
  error: string | null;
  updateSetting: (key: string, value: any) => Promise<boolean>; // eslint-disable-line @typescript-eslint/no-explicit-any
}

// Create the context with a default value
const SettingsContext = createContext<SettingsContextValue | null>(null);

// Custom hook to use settings
export const useSettings = (): SettingsContextValue => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};

interface SettingsProviderProps {
  children: ReactNode;
}

// Provider component
export const SettingsProvider: React.FC<SettingsProviderProps> = ({ children }) => {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/settings`);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: Settings = await response.json();
        setSettings(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  // Method to update a specific setting
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const updateSetting = async (key: string, value: any): Promise<boolean> => {
    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ [key]: value }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setSettings((prev) =>
        prev
          ? {
              ...prev,
              [key]: value,
            }
          : null,
      );

      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      return false;
    }
  };

  const value: SettingsContextValue = {
    settings,
    loading,
    error,
    updateSetting,
  };

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
};
