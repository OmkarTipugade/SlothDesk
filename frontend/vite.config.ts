import react from '@vitejs/plugin-react'
import { defineConfig, configDefaults } from 'vitest/config'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    globals: true,
    exclude: [...configDefaults.exclude, '**/node_modules/**'],
  },
})
