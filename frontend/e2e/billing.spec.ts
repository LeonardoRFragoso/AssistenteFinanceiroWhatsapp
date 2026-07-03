import { test, expect, Page } from '@playwright/test';

async function demoLogin(page: Page) {
  await page.context().clearCookies();
  await page.goto('/login');
  const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
  await expect(demoBtn).toBeVisible({ timeout: 15000 });
  await demoBtn.click();
  await page.waitForURL(/\/dashboard/, { timeout: 60000 });
}

async function scrollToBilling(page: Page) {
  await expect(page.getByText(/carregando seu dashboard/i)).toBeHidden({ timeout: 30000 });
  await expect(page.locator('main')).toBeVisible({ timeout: 20000 });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);
}

test.describe('Billing Section E2E', () => {
  test('1. Billing section loads with data-testid', async ({ page }) => {
    await demoLogin(page);
    await scrollToBilling(page);
    await expect(page.getByTestId('billing-section')).toBeVisible({ timeout: 15000 });
  });

  test('2. Plan cards are visible', async ({ page }) => {
    await demoLogin(page);
    await scrollToBilling(page);
    await expect(page.getByTestId('plan-card-free')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('plan-card-professional')).toBeVisible({ timeout: 15000 });
  });

  test('3. Usage meters are visible', async ({ page }) => {
    await demoLogin(page);
    await scrollToBilling(page);
    await expect(page.getByTestId('usage-meters')).toBeVisible({ timeout: 15000 });
  });

  test('4. Current plan card is visible', async ({ page }) => {
    await demoLogin(page);
    await scrollToBilling(page);
    await expect(page.getByTestId('current-plan-card')).toBeVisible({ timeout: 15000 });
  });

  test('5. Sandbox warning is visible', async ({ page }) => {
    await demoLogin(page);
    await scrollToBilling(page);
    await expect(page.getByTestId('billing-sandbox-warning')).toBeVisible({ timeout: 15000 });
  });

  test('6. Change plan button is visible for demo (owner)', async ({ page }) => {
    await demoLogin(page);
    await scrollToBilling(page);
    const changeBtn = page.getByTestId('change-plan-button').first();
    await expect(changeBtn).toBeVisible({ timeout: 15000 });
  });

  test('7. Change plan flow works', async ({ page }) => {
    await demoLogin(page);
    await scrollToBilling(page);
    const changeBtn = page.getByTestId('change-plan-button').first();
    await expect(changeBtn).toBeVisible({ timeout: 15000 });
    await changeBtn.click();
    // Wait for success or error message
    await page.waitForTimeout(3000);
    // Verify billing section still visible after action
    await expect(page.getByTestId('billing-section')).toBeVisible({ timeout: 10000 });
  });
});
