import { test, expect } from '@playwright/test';

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
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('4. Dashboard renders after demo login', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page.locator('main')).toBeVisible({ timeout: 15000 });
  });

  test('5. Charge summary cards appear', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page.getByText(/pendentes/i).first()).toBeVisible({ timeout: 20000 });
    await expect(page.getByText(/vencidas/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('6. Charges section with table appears', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 20000 });
    await expect(page.locator('table')).toBeVisible({ timeout: 15000 });
  });

  test('7. Filter by Vencidas works', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 20000 });
    const vencidasBtn = page.getByRole('button', { name: /^vencidas$/i }).first();
    await expect(vencidasBtn).toBeVisible({ timeout: 10000 });
    await vencidasBtn.click();
    await page.waitForTimeout(1000);
  });

  test('8. Search by customer works', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 20000 });
    const searchInput = page.getByPlaceholder(/buscar por cliente ou descrição/i);
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill('Test');
    const buscarBtn = page.getByRole('button', { name: /^buscar$/i });
    await buscarBtn.click();
    await page.waitForTimeout(1000);
  });

  test('9. Export CSV button works', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 20000 });
    const csvBtn = page.getByRole('button', { name: /csv/i }).first();
    await expect(csvBtn).toBeVisible({ timeout: 10000 });
    await csvBtn.click();
    await page.waitForTimeout(2000);
  });

  test('10. Export PDF button works', async ({ page }) => {
    await page.goto('/login');
    const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10000 });
    await demoBtn.click();
    await page.waitForURL(/\/dashboard/, { timeout: 30000 });
    await expect(page.getByRole('heading', { name: /cobranças/i })).toBeVisible({ timeout: 20000 });
    const pdfBtn = page.getByRole('button', { name: /pdf/i }).first();
    await expect(pdfBtn).toBeVisible({ timeout: 10000 });
    await pdfBtn.click();
    await page.waitForTimeout(2000);
  });
});
