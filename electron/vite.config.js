import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  base: './', // Use relative paths for Electron

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer/workflow'),
      '@hitl': resolve(__dirname, 'src/renderer/hitl'),
      '@reminder': resolve(__dirname, 'src/renderer/reminder'),
    },
  },

  build: {
    outDir: resolve(__dirname, 'dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/renderer/workflow/index.html'),
        hitl: resolve(__dirname, 'src/renderer/hitl/index.html'),
        'image-preview': resolve(__dirname, 'src/renderer/image-preview/index.html'),
        reminder: resolve(__dirname, 'src/renderer/reminder/index.html'),
      },
    },
  },
  server: {
    port: 3000,
  },
  css: {
    postcss: resolve(__dirname, 'postcss.config.js'),
  },
});
