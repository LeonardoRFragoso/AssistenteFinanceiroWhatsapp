import { test, expect, Page } from '@playwright/test';
import path from 'path';

const SCREENSHOTS_DIR = path.resolve(__dirname, '../../docs/assets');

async function demoLoginAndWait(page: Page) {
  await page.goto('/login');
  const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
  await expect(demoBtn).toBeVisible({ timeout: 15000 });
  await demoBtn.click();
  await page.waitForURL(/\/dashboard/, { timeout: 45000 });
  await expect(page.getByText(/carregando seu dashboard/i)).toBeHidden({ timeout: 30000 });
}

test.describe('Generate screenshots', () => {
  test('landing page', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/landing.png`, fullPage: true });
  });

  test('login demo', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/login-demo.png`, fullPage: true });
  });

  test('dashboard overview', async ({ page }) => {
    await demoLoginAndWait(page);
    await expect(page.getByText(/pendentes/i).first()).toBeVisible({ timeout: 20000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/dashboard-overview.png`, fullPage: true });
  });

  test('charges table', async ({ page }) => {
    await demoLoginAndWait(page);
    await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 20000 });
    await expect(page.locator('table')).toBeVisible({ timeout: 15000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/charges-table.png`, fullPage: true });
  });

  test('analytics cards', async ({ page }) => {
    await demoLoginAndWait(page);
    await expect(page.getByText(/taxa de conversão/i)).toBeVisible({ timeout: 20000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/analytics.png`, fullPage: true });
  });

  test('export area', async ({ page }) => {
    await demoLoginAndWait(page);
    await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 20000 });
    const csvBtn = page.getByRole('button', { name: /csv/i }).first();
    await expect(csvBtn).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/export-pdf.png`, fullPage: true });
  });
});
