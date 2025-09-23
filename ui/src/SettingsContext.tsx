import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { API_BASE_URL } from './App';
import { Settings } from './models/Settings';

// Define the context value type
interface SettingsContextValue {
  settings: Settings | null;
  loading: boolean;
  error: string | null;
  updateSetting: (key: keyof Settings, value: Settings[keyof Settings]) => Promise<boolean>;
  refreshSettings: () => Promise<void>;
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

  // Function to load settings from API
  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/settings`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: Settings = await response.json();
      setSettings(data);
      setError(null); // Clear any previous errors
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  // Method to update a specific setting
  const updateSetting = async (key: keyof Settings, value: Settings[keyof Settings]): Promise<boolean> => {
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

  // Method to refresh settings from the server
  const refreshSettings = async () => {
    await loadSettings();
  };

  const value: SettingsContextValue = {
    settings,
    loading,
    error,
    updateSetting,
    refreshSettings,
  };

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
};
