import { test, expect, Page } from '@playwright/test';
import path from 'path';

const SCREENSHOTS_DIR = path.resolve(__dirname, '../../docs/assets');

async function demoLoginAndWait(page: Page) {
  await page.context().clearCookies();
  await page.goto('/login');
  const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
  await expect(demoBtn).toBeVisible({ timeout: 15000 });
  await demoBtn.click();
  await page.waitForURL(/\/dashboard/, { timeout: 60000 });
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
    await expect(page.locator('table').first()).toBeVisible({ timeout: 15000 });
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
    // Scroll to charges section
    const chargesHeading = page.getByRole('heading', { name: /cobranças/i });
    await chargesHeading.scrollIntoViewIfNeeded({ timeout: 20000 });
    await expect(chargesHeading).toBeVisible({ timeout: 20000 });
    const csvBtn = page.getByRole('button', { name: /csv/i }).first();
    await expect(csvBtn).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/export-pdf.png`, fullPage: true });
  });

  test('customer intelligence — all tabs', async ({ page }) => {
    await demoLoginAndWait(page);
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000);
    const section = page.getByTestId('customer-intelligence-section');
    await expect(section).toBeVisible({ timeout: 30000 });
    await expect(section.getByText(/carregando/i)).toBeHidden({ timeout: 20000 });
    await page.waitForTimeout(1000);
    // Customers tab screenshot
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/customer-intelligence.png`, fullPage: true });
    // Templates tab
    const templatesTab = page.getByTestId('templates-tab');
    await templatesTab.click({ force: true });
    await expect(section.getByText(/carregando/i)).toBeHidden({ timeout: 20000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/message-templates.png`, fullPage: true });
    // Collection rules tab
    const collectionTab = page.getByTestId('collection-rules-tab');
    await collectionTab.click({ force: true });
    await expect(section.getByText(/carregando/i)).toBeHidden({ timeout: 20000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/collection-rules.png`, fullPage: true });
  });

  test('Sprint 10 - Advanced Analytics screenshot', async ({ page }) => {
    await demoLoginAndWait(page);
    const analyticsSection = page.getByTestId('advanced-analytics-section');
    await expect(analyticsSection).toBeVisible({ timeout: 30000 });
    await analyticsSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/advanced-analytics.png`, fullPage: false });
  });

  test('Sprint 11 - Organization & Members screenshot', async ({ page }) => {
    await demoLoginAndWait(page);
    const orgSection = page.getByTestId('organization-section');
    await expect(orgSection).toBeVisible({ timeout: 30000 });
    await orgSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(3000);
    await page.screenshot({ path: `${SCREENSHOTS_DIR}/organization-members.png`, fullPage: false });
  });
});
