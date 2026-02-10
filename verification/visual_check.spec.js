import { test, expect } from '@playwright/test';

test('dashboard visual check', async ({ page }) => {
  await page.goto('http://localhost:5173');
  // Wait for the app to load
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'verification/dashboard_fixed.png' });
});
