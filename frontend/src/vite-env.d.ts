/// <reference types="vite/client" />

interface ViteTypeOptions {
  strictImportMetaEnv: unknown
}

interface ImportMetaEnv {
  /** Origin of the Django API, no trailing slash. Undefined unless a real .env/OS env var sets
   * it -- there is no .env file in this repo, so this is undefined in dev, test and (unless set)
   * production; lib/api.ts falls back to '' (relative /api, matching the dev proxy). */
  readonly VITE_API_BASE_URL?: string
}
