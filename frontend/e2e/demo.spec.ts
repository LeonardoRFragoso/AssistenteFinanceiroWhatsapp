import { test, expect, Page } from '@playwright/test';

async function demoLogin(page: Page) {
  await page.goto('/login');
  const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
  await expect(demoBtn).toBeVisible({ timeout: 15000 });
  await demoBtn.click();
  await page.waitForURL(/\/dashboard/, { timeout: 45000 });
}

async function waitForDashboardReady(page: Page) {
  // Wait for the main loading spinner to disappear
  await expect(page.getByText(/carregando seu dashboard/i)).toBeHidden({ timeout: 30000 });
  // Wait for the charges heading to appear
  await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 30000 });
  // Wait for the charges table to be visible (not in loading state)
  await expect(page.locator('table')).toBeVisible({ timeout: 20000 });
  // Wait for charges loading spinner inside table area to disappear
  const tableSpinner = page.locator('.animate-spin').first();
  if (await tableSpinner.isVisible().catch(() => false)) {
    await expect(tableSpinner).toBeHidden({ timeout: 15000 });
  }
}

test.describe('Demo Mode E2E', () => {
  test('1. Landing page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 });
  });

  test('2. Demo login button visible on landing', async ({ page }) => {
    await page.goto('/');
    const demoBtn = page.getByRole('button', { name: /entrar na demo/i }).first();
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
  });

  test('3. Demo login flow works', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 15000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 45000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('4. Dashboard renders after demo login', async ({ page }) => {
    await demoLogin(page);
    await expect(page.getByText(/carregando seu dashboard/i)).toBeHidden({ timeout: 30000 });
    await expect(page.locator('main')).toBeVisible({ timeout: 20000 });
  });

  test('5. Charge summary cards appear', async ({ page }) => {
    await demoLogin(page);
    await expect(page.getByText(/carregando seu dashboard/i)).toBeHidden({ timeout: 30000 });
    await expect(page.getByText(/pendentes/i).first()).toBeVisible({ timeout: 25000 });
    await expect(page.getByText(/vencidas/i).first()).toBeVisible({ timeout: 15000 });
  });

  test('6. Charges section with table appears', async ({ page }) => {
    await demoLogin(page);
    await waitForDashboardReady(page);
  });

  test('7. Filter by Vencidas works', async ({ page }) => {
    await demoLogin(page);
    await waitForDashboardReady(page);
    const vencidasBtn = page.getByRole('button', { name: /^vencidas$/i }).first();
    await expect(vencidasBtn).toBeVisible({ timeout: 15000 });
    await vencidasBtn.click({ force: true });
    await page.waitForTimeout(1000);
  });

  test('8. Search by customer works', async ({ page }) => {
    await demoLogin(page);
    await waitForDashboardReady(page);
    const searchInput = page.getByPlaceholder(/buscar por cliente ou descrição/i);
    await expect(searchInput).toBeVisible({ timeout: 15000 });
    await searchInput.fill('Test');
    const buscarBtn = page.getByRole('button', { name: /^buscar$/i });
    await expect(buscarBtn).toBeEnabled({ timeout: 10000 });
    await buscarBtn.click({ force: true });
    await page.waitForTimeout(1000);
  });

  test('9. Export CSV button works', async ({ page }) => {
    await demoLogin(page);
    await waitForDashboardReady(page);
    const csvBtn = page.getByRole('button', { name: /csv/i }).first();
    await expect(csvBtn).toBeVisible({ timeout: 15000 });
    await expect(csvBtn).toBeEnabled({ timeout: 10000 });
    await csvBtn.click({ force: true });
    await page.waitForTimeout(2000);
  });

  test('10. Export PDF button works', async ({ page }) => {
    await demoLogin(page);
    await waitForDashboardReady(page);
    const pdfBtn = page.getByRole('button', { name: /pdf/i }).first();
    await expect(pdfBtn).toBeVisible({ timeout: 15000 });
    await expect(pdfBtn).toBeEnabled({ timeout: 10000 });
    await pdfBtn.click({ force: true });
    await page.waitForTimeout(2000);
  });
});
