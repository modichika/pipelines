import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';
import { generatedCjsBridge } from './vite-plugins/generated-cjs-bridge';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const proxyTarget = process.env.KFP_API_TARGET || 'http://localhost:8888';
const mlmdTarget = 'http://localhost:9090';
const proxyPaths = [
  '/api',
  '/apis',
  '/apps',
  '/artifacts',
  '/hub',
  '/k8s',
  '/system',
  '/visualizations',
];

const proxy = proxyPaths.reduce<Record<string, { target: string; changeOrigin: boolean; headers?: Record<string, string> }>>(
  (acc, prefix) => {
    acc[prefix] = {
      target: proxyTarget,
      changeOrigin: true,
      headers: {
        'kubeflow-userid': 'user@example.com',
      },
    };
    return acc;
  },
  {
    '/ml_metadata': {
      target: mlmdTarget,
      changeOrigin: true,
    },
  },
);

export default defineConfig(({ mode }) => ({
  base: './',
  plugins: [
    generatedCjsBridge(),
    react(),
    mode === 'analyze' &&
      visualizer({
        filename: 'build/bundle-report.html',
        gzipSize: true,
        brotliSize: true,
        open: true,
      }),
  ].filter(Boolean),
  resolve: {
    alias: {
      src: path.resolve(__dirname, 'src'),
      'react-virtualized': path.resolve(
        __dirname,
        'node_modules/react-virtualized/dist/commonjs/index.js',
      ),
    },
  },
  server: {
    port: 3000,
    proxy,
  },
  optimizeDeps: {
    exclude: ['@mui/material/colors'],
  },
  build: {
    target: 'es2015',
    outDir: 'build',
    assetsDir: 'static',
    sourcemap: true,
    // TODO(#13018): Remove MLMD path after Phase 2 migration
    commonjsOptions: {
      include: [/node_modules/, /src\/third_party\/mlmd\/generated/],
    },
  },
}));
