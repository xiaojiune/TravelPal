import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import prettier from 'eslint-config-prettier'

export default tseslint.config(
  { ignores: ['node_modules', 'dist'] },

  // JS / TS 文件
  ...tseslint.configs.recommended.map(c => ({
    ...c,
    files: ['**/*.{ts,mts,js,mjs}'],
  })),

  // Vue 文件
  ...pluginVue.configs['flat/recommended'].map(c => ({
    ...c,
    files: ['**/*.vue'],
  })),
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        sourceType: 'module',
      },
    },
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/require-v-for-key': 'warn',
    },
  },

  // 关闭与 Prettier 冲突的规则
  prettier,
)
