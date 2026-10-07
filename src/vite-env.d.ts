/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_FACTCHECK_API_URL?: string;
  readonly VITE_FACTCHECK_PROXY_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
