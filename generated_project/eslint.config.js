module.exports = [
  {
    files: ["*.ts"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off"
    },
    languageOptions: {
      parser: "@typescript-eslint/parser",
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: "module"
      }
    }
  },
  {
    files: ["*.js"],
    rules: {
      "no-console": "off"
    },
    languageOptions: {
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: "module"
      }
    }
  },
  {
    files: ["*.jsx"],
    rules: {
      "react/jsx-uses-react": "off"
    },
    languageOptions: {
      parser: "@typescript-eslint/parser",
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: "module",
        ecmaFeatures: {
          jsx: true
        }
      }
    }
  }
];