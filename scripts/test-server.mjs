import { build, preview } from "vite";

process.env.VITE_FACTCHECK_API_URL = "http://127.0.0.1:5174";
await build();
const server = await preview({
  preview: { host: "127.0.0.1", port: 5174, strictPort: true },
});
server.printUrls();
