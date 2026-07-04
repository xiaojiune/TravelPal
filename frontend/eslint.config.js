import pluginVue from 'eslint-plugin-vue'

export default [
  {
    ignores: ['node_modules', 'dist'],
  },
  {
    files: ['**/*.js', '**/*.vue'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'module',
      globals: {
        browser: true,
        node: true,
      },
    },
    plugins: {
      vue: pluginVue,
    },
    rules: {
      semi: ['error', 'never'],
      quotes: ['error', 'single'],
    },
  },
  ...pluginVue.configs['flat/essential'],
]
