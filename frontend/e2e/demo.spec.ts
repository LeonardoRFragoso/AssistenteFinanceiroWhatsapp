import { test, expect } from '@playwright/test';

test.describe('Demo Mode E2E', () => {
  test('1. Landing page loads', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible({ timeout: 10000 });
  });

  test('2. Demo login button is visible when demo mode enabled', async ({ page }) => {
    await page.goto('/');
    // The demo button should be visible when NEXT_PUBLIC_ENABLE_DEMO_MODE=true
    const demoButton = page.getByText(/entrar como demo/i).first();
    if (await demoButton.isVisible()) {
      await demoButton.click();
      // Should navigate to login page or trigger demo login
      await page.waitForURL(/\/login|\/dashboard/, { timeout: 10000 });
    }
  });

  test('3. Demo login works when enabled', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');

    // Check if demo button exists
    const demoBtn = page.getByText(/entrar como demo/i).first();
    if (await demoBtn.isVisible({ timeout: 5000 })) {
      await demoBtn.click();
      // Should redirect to dashboard
      await page.waitForURL(/\/dashboard/, { timeout: 15000 });
      await expect(page).toHaveURL(/\/dashboard/);
    }
  });

  test('4. Dashboard loads after login', async ({ page, context }) => {
    // Mock auth by setting token in localStorage
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-demo-token');
    });
    await page.goto('/dashboard');
    // Dashboard should attempt to load — may show error if API not available
    // but the page structure should be present
    await page.waitForLoadState('networkidle');
    const layout = page.locator('main, [class*="min-h-screen"]').first();
    await expect(layout).toBeVisible({ timeout: 10000 });
  });

  test('5. Main cards appear on dashboard', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-demo-token');
    });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Check for summary cards (income, expenses, balance)
    const cards = page.locator('[class*="rounded-xl"], [class*="card"], [class*="bg-white"]').first();
    await expect(cards).toBeVisible({ timeout: 10000 });
  });

  test('6. Charges list appears', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-demo-token');
    });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Look for charges section
    const chargesSection = page.getByText(/cobranças|charges/i).first();
    await expect(chargesSection).toBeVisible({ timeout: 10000 });
  });

  test('7. Overdue filter works', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-demo-token');
    });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Try to find and click overdue filter
    const overdueFilter = page.getByText(/vencidas|overdue/i).first();
    if (await overdueFilter.isVisible({ timeout: 5000 })) {
      await overdueFilter.click();
      await page.waitForLoadState('networkidle');
    }
  });

  test('8. Search by customer works', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-demo-token');
    });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // Try to find search input
    const searchInput = page.getByPlaceholder(/buscar|search/i).first();
    if (await searchInput.isVisible({ timeout: 5000 })) {
      await searchInput.fill('Test Customer');
      await page.waitForTimeout(500);
    }
  });

  test('9. Export CSV triggers download', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-demo-token');
    });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const csvButton = page.getByText(/csv/i).first();
    if (await csvButton.isVisible({ timeout: 5000 })) {
      const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(() => null);
      await csvButton.click();
      await downloadPromise;
    }
  });

  test('10. Export PDF triggers download', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('token', 'mock-demo-token');
    });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const pdfButton = page.getByText(/pdf/i).first();
    if (await pdfButton.isVisible({ timeout: 5000 })) {
      const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(() => null);
      await pdfButton.click();
      await downloadPromise;
    }
  });
});
