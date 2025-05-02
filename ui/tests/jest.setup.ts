import '@testing-library/jest-dom';

// Mock TextEncoder and TextDecoder which are used by some libraries but not available in JSDOM by default
import { TextEncoder, TextDecoder } from 'util';

global.TextEncoder = TextEncoder;
// Assign TextDecoder to global. Need to cast as any because the types might not align perfectly
global.TextDecoder = TextDecoder as any; // eslint-disable-line @typescript-eslint/no-explicit-any

// You might need to mock other browser APIs if your components use them
// Example: Mocking matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});
