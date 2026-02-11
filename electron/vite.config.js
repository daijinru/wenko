import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  base: './', // Use relative paths for Electron

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer/workflow'),
      '@ecs': resolve(__dirname, 'src/renderer/ecs'),
      '@reminder': resolve(__dirname, 'src/renderer/reminder'),
      '@shared': resolve(__dirname, 'src/shared'),
    },
  },

  build: {
    outDir: resolve(__dirname, 'dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'src/renderer/workflow/index.html'),
        ecs: resolve(__dirname, 'src/renderer/ecs/index.html'),
        'image-preview': resolve(__dirname, 'src/renderer/image-preview/index.html'),
        reminder: resolve(__dirname, 'src/renderer/reminder/index.html'),
      },
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-radix': [
            '@radix-ui/react-checkbox',
            '@radix-ui/react-dialog',
            '@radix-ui/react-slider',
            '@radix-ui/react-slot',
            '@radix-ui/react-tabs',
          ],
        },
      },
    },
  },
  server: {
    port: 3000,
    strictPort: true,
  },
  css: {
    postcss: resolve(__dirname, 'postcss.config.js'),
  },
});
