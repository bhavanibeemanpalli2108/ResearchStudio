import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': process.env.RESEARCH_API_URL ?? 'http://127.0.0.1:8000' },
  },
  build: { chunkSizeWarningLimit: 900 },
  test: {
    include: ['src/test/**/*.test.ts', 'src/test/**/*.test.tsx'],
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: false,
  },
});
