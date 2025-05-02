// eslint.config.js
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactRecommended from "eslint-plugin-react/configs/recommended.js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import prettierConfig from "eslint-config-prettier"; // Import prettier config last

export default tseslint.config(
  // Global ignores
  {
    ignores: [
        "node_modules/",
        "build/", // CRA build output directory
        // Add other ignores if needed, e.g., coverage/
      ],
  },

  // Base JS config
  js.configs.recommended,

  // TypeScript configs
  ...tseslint.configs.recommended,

  // React specific configs
  {
    files: ["**/*.{ts,tsx}"], // Target TS/TSX files
    ...reactRecommended, // Apply React recommended rules
    settings: {
      react: {
        version: "detect", // Automatically detect React version
      },
    },
    languageOptions: {
        ...reactRecommended.languageOptions, // Inherit language options
        parserOptions: {
            ecmaFeatures: { jsx: true }, // Ensure JSX is enabled
        },
        globals: {
            ...globals.browser, // Add browser globals
            ...globals.node, // Add Node globals (useful for some configs/scripts)
            ...globals.jest // Add Jest globals for test files
        }
    },
    plugins: {
        ...reactRecommended.plugins, // Inherit plugins
        "react-hooks": reactHooks, // Add react-hooks plugin
    },
    rules: {
        ...reactRecommended.rules, // Inherit rules
        ...reactHooks.configs.recommended.rules, // Add react-hooks recommended rules
        "react/react-in-jsx-scope": "off", // Not needed with new JSX transform
        "react/jsx-uses-react": "off", // Not needed with new JSX transform
        // Add any project-specific rules here
    },
  },

  // Config for CommonJS files (like config files, mocks)
  {
    files: ["jest.config.cjs", "tests/__mocks__/fileMock.js"],
    languageOptions: {
      sourceType: "commonjs",
      globals: {
          ...globals.node, // Define Node.js globals like 'module', 'require'
      }
    },
  },

  // Prettier config (MUST be last)
  prettierConfig,
);
