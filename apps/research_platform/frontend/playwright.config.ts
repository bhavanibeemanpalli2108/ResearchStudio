import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './e2e',
  timeout: 120000,
  expect: { timeout: 20000 },
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.PLATFORM_URL ?? 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run dev -- --port ${process.env.PLATFORM_FRONTEND_PORT ?? '5173'} --strictPort`,
    url: process.env.PLATFORM_URL ?? 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 30000,
  },
});
