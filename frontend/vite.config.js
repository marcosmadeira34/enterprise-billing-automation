import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
// https://vite.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
            "@components": path.resolve(__dirname, "./src/components"),
            "@pages": path.resolve(__dirname, "./src/pages"),
            "@hooks": path.resolve(__dirname, "./src/hooks"),
            "@services": path.resolve(__dirname, "./src/services"),
            "@store": path.resolve(__dirname, "./src/store"),
            "@types": path.resolve(__dirname, "./src/types"),
            "@utils": path.resolve(__dirname, "./src/utils"),
        },
    },
    server: {
        port: 5173,
        strictPort: true,
        host: true,
        proxy: {
            "/api": {
                target: "http://api:8000",
                changeOrigin: true,
                secure: false,
            },
        },
    },
    preview: {
        port: 4173,
        strictPort: true,
        host: true,
    },
    build: {
        target: "es2022",
        outDir: "dist",
        sourcemap: true,
        rollupOptions: {
            output: {
                manualChunks: {
                    vendor: ["react", "react-dom"],
                    router: ["react-router-dom"],
                    query: ["@tanstack/react-query"],
                    charts: ["recharts"],
                    table: ["@tanstack/react-table"],
                },
            },
        },
    },
});
