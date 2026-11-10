import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      coverage: {
        provider: "v8",
        reporter: ["text", "html", "lcov"],
        exclude: [
          "node_modules/",
          "src/test/",
          "src/**/*.d.ts",
          "src/main.tsx",
          "vite.config.ts",
          "vitest.config.ts",
        ],
        thresholds: {
          lines: 70,
          branches: 70,
          functions: 70,
          statements: 70,
        },
      },
    },
  })
);

