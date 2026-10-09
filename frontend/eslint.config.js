import eslintPluginVue from 'eslint-plugin-vue'
import prettierConfig from '@vue/eslint-config-prettier'

export default [
  ...eslintPluginVue.configs['flat/recommended'],
  prettierConfig,
  {
    ignores: ['dist/**', 'node_modules/**'],
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'error',
    },
  },
]
