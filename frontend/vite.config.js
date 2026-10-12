import {
  defineConfig,
} from "vite";

import react from
  "@vitejs/plugin-react";


export default defineConfig({

  plugins: [
    react(),
  ],

  server: {

    host: "127.0.0.1",

    port: 5173,

    proxy: {

      "/lessons": {
        target:
          "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/qcm": {
        target:
          "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/attempts": {
        target:
          "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/progress": {
        target:
          "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/exams": {
        target:
          "http://127.0.0.1:8000",
        changeOrigin: true,
      },

    },

  },

});