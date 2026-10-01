import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// BASE_PATH is "/imputation-lab/" on GitHub Pages and "/" for local use.
export default defineConfig({
  base: process.env.BASE_PATH ?? '/',
  plugins: [vue()],
  worker: { format: 'es' },
  test: { include: ['tests/**/*.test.ts'] },
})
