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

      "/auth": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/lessons": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/qcm": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/attempts": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/progress": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/exams": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/summary": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/explain": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/translate": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/chat": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/file_analysis": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/topic": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

      "/review": {
        target:
          "https://klearstudy-backend-1fvgp1mv5h8lur.sabay.com",
        changeOrigin: true,
      },

    },

  },

});