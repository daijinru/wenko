import { defineManifest } from '@crxjs/vite-plugin'
import packageData from '../package.json'

//@ts-ignore
const isDev = process.env.NODE_ENV == 'development'

export default defineManifest({
  name: `${packageData.displayName || packageData.name}${isDev ? ` ➡️ Dev` : ''}`,
  description: packageData.description,
  version: packageData.version,
  manifest_version: 3,
  icons: {
    16: 'img/logo-16.png',
    32: 'img/logo-32.png',
    48: 'img/logo-48.png',
    128: 'img/logo-128.png',
  },
  action: {
    default_popup: 'popup.html',
    default_icon: 'img/logo-48.png',
  },
  options_page: 'options.html',
  devtools_page: 'devtools.html',
  background: {
    service_worker: 'src/background/index.ts',
    type: 'module',
  },
  // 旧 content_scripts 注释或删除，改用后台注入
  // content_scripts: [],
  side_panel: {
    default_path: 'sidepanel.html',
  },
  host_permissions: ['http://*/*', 'https://*/*'],
  web_accessible_resources: [
    {
      resources: [
        'img/logo-16.png',
        'img/logo-32.png',
        'img/logo-48.png',
        'img/logo-128.png',
        'inject/build/contentScriptReact.iife.js', // React打包产物必须允许访问
        "inject/inject.js",
      ],
      matches: ['http://*/*', 'https://*/*'],
    },
  ],
  permissions: ['sidePanel', 'storage', 'contextMenus', 'activeTab', 'tabs', 'scripting'],
  chrome_url_overrides: {
    newtab: 'newtab.html',
  },
})