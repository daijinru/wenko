import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import chokidar from 'chokidar'
import windi from 'vite-plugin-windicss'

const srcDir = path.resolve(__dirname, 'build')
const destDir = path.resolve(__dirname, '../build/inject/build')
const injectJS = path.resolve(__dirname, './inject.js')
const injectJSDest = path.resolve(__dirname, '../build/inject/inject.js')

function copyFiles() {
  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true })
  }
  fs.readdir(srcDir, (err, files) => {
    if (err) {
      console.error('Read build directory error:', err)
      return
    }
    files.forEach(file => {
      const srcPath = path.join(srcDir, file)
      const destPath = path.join(destDir, file)
      fs.copyFile(srcPath, destPath, (copyErr) => {
        if (copyErr) {
          console.error(`Failed to copy ${file}:`, copyErr)
        } else {
          console.log(`Copied ${file} to ${destDir}`)
        }
      })
    })
  })
  fs.copyFile(injectJS, injectJSDest, (copyErr) => {
    if (copyErr) {
      console.error(`Failed to copy inject.js:`, copyErr)
    } else {
      console.log(`Copied inject.js to ${injectJSDest}`)
    }
  })
}

export default defineConfig(({ mode }) => {
  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true })
  }

  const watcher = chokidar.watch([srcDir, injectJS], {
    ignoreInitial: true,
  })

  watcher.on('add', copyFiles)
  watcher.on('change', copyFiles)
  watcher.on('unlink', copyFiles)

  return {
    define: {
      'process.env.NODE_ENV': JSON.stringify(mode),
    },
    plugins: [
      windi(),
      react(),
    ],
    build: {
      lib: {
        entry: path.resolve(__dirname, 'src/reactApp.tsx'),
        name: 'contentScriptReact',
        fileName: 'contentScriptReact',
        formats: ['iife'],
      },
      outDir: srcDir,
      emptyOutDir: true,
      watch: {}, // 继续开启监听构建
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
  }
})
