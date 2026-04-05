import path from 'node:path'
import { fileURLToPath } from 'node:url'
import type { NextConfig } from 'next'

const appRoot = path.dirname(fileURLToPath(import.meta.url))

const nextConfig: NextConfig = {
  turbopack: {
    // Avoid intermittent root mis-detection in the nested frontend/backend repo layout.
    root: appRoot,
  },
}

export default nextConfig
