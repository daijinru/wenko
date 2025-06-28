import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => ({
  define: {
    'process.env.NODE_ENV': JSON.stringify(mode), // 注入当前构建模式，'development' 或 'production'
  },
  plugins: [react()],
  build: {
    lib: {
      entry: path.resolve(__dirname, 'reactApp.tsx'),
      name: 'contentScriptReact',
      fileName: 'contentScriptReact',
      formats: ['iife'],
    },
    outDir: path.resolve(__dirname, 'build'),
    emptyOutDir: true,
    watch: {},  // 开启监听模式
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname),
    },
  },
  esbuild: {
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment',
  },
}))