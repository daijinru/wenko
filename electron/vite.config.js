import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  base: './', // Use relative paths for Electron
  root: 'src/renderer/workflow', // Set root to the workflow directory

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer/workflow'),
    },
  },

  build: {
    outDir: resolve(__dirname, 'dist'), // Output to project root's dist folder
    emptyOutDir: true,
    rollupOptions: {
      // No need to specify input if index.html is in root
    },
  },
  server: {
    port: 3000,
  },
  css: {
    postcss: resolve(__dirname, 'postcss.config.js'),
  },
});
