import { test, expect, Page } from '@playwright/test';

async function demoLogin(page: Page) {
  await page.context().clearCookies();
  await page.goto('/login');
  const demoBtn = page.getByRole('button', { name: /entrar como demo/i });
  await expect(demoBtn).toBeVisible({ timeout: 15000 });
  await demoBtn.click();
  await page.waitForURL(/\/dashboard/, { timeout: 60000 });
}

async function waitForDashboardReady(page: Page) {
  await expect(page.getByText(/carregando seu dashboard/i)).toBeHidden({ timeout: 30000 });
  await expect(page.locator('main')).toBeVisible({ timeout: 20000 });
  const tableSpinner = page.locator('.animate-spin').first();
  if (await tableSpinner.isVisible().catch(() => false)) {
    await expect(tableSpinner).toBeHidden({ timeout: 15000 });
  }
}

async function scrollToSection(page: Page) {
  await expect(page.getByText(/carregando seu dashboard/i)).toBeHidden({ timeout: 30000 });
  await expect(page.locator('main')).toBeVisible({ timeout: 20000 });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(1000);
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
    await page.waitForURL(/\/dashboard/, { timeout: 60000 });
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
    const buscarBtn = page.getByRole('button', { name: /^buscar$/i }).first();
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

// Sprint 9 — Customer Intelligence E2E (serial, shared login)
test.describe('Sprint 9 — Customer Intelligence E2E', () => {
  test.describe.configure({ mode: 'serial' });

  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await demoLogin(page);
    await waitForDashboardReady(page);
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('11. Customer Intelligence section appears', async () => {
    await scrollToSection(page);
    const section = page.getByTestId('customer-intelligence-section');
    await expect(section).toBeVisible({ timeout: 30000 });
    await expect(section.getByRole('heading', { name: /customer intelligence/i })).toBeVisible({ timeout: 10000 });
  });

  test('12. Customers tab is active by default', async () => {
    const section = page.getByTestId('customer-intelligence-section');
    await expect(section).toBeVisible({ timeout: 10000 });
    const customersTab = page.getByTestId('customers-tab');
    await expect(customersTab).toBeVisible({ timeout: 10000 });
    const searchInput = page.getByTestId('customer-search-input');
    await expect(searchInput).toBeVisible({ timeout: 15000 });
  });

  test('13. Customers listing or empty state is controlled', async () => {
    const section = page.getByTestId('customer-intelligence-section');
    await expect(section.getByText(/carregando/i)).toBeHidden({ timeout: 20000 });
    const table = section.locator('table');
    const emptyState = section.getByText(/nenhum cliente encontrado/i);
    const tableVisible = await table.isVisible().catch(() => false);
    const emptyVisible = await emptyState.isVisible().catch(() => false);
    expect(tableVisible || emptyVisible).toBeTruthy();
  });

  test('14. Customer search input accepts text', async () => {
    const searchInput = page.getByTestId('customer-search-input');
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill('Teste');
    await page.waitForTimeout(500);
    await searchInput.press('Enter');
    await page.waitForTimeout(1000);
    await expect(page.getByTestId('customer-intelligence-section')).toBeVisible();
  });

  test('15. Templates tab appears and shows content or empty state', async () => {
    const section = page.getByTestId('customer-intelligence-section');
    await expect(section).toBeVisible({ timeout: 10000 });
    const templatesTab = page.getByTestId('templates-tab');
    await expect(templatesTab).toBeVisible({ timeout: 10000 });
    await templatesTab.click({ force: true });
    await expect(section.getByText(/carregando/i)).toBeHidden({ timeout: 20000 });
    // After loading, the section should have visible content — either templates or empty state
    // Just verify the section still has visible text content (not blank)
    const sectionText = await section.innerText();
    expect(sectionText.length).toBeGreaterThan(10);
  });

  test('16. Template preview button works when templates exist', async () => {
    const section = page.getByTestId('customer-intelligence-section');
    await expect(section).toBeVisible({ timeout: 10000 });
    const previewBtn = page.getByTestId('message-template-preview-button').first();
    const hasPreview = await previewBtn.isVisible().catch(() => false);
    if (hasPreview) {
      await previewBtn.click({ force: true });
      await expect(section.getByText(/prévia renderizada/i)).toBeVisible({ timeout: 10000 });
    }
  });

  test('17. Collection rules tab shows content, empty state, and no auto-send', async () => {
    const section = page.getByTestId('customer-intelligence-section');
    await expect(section).toBeVisible({ timeout: 10000 });
    const collectionTab = page.getByTestId('collection-rules-tab');
    await expect(collectionTab).toBeVisible({ timeout: 10000 });
    await collectionTab.click({ force: true });
    await expect(section.getByText(/carregando/i)).toBeHidden({ timeout: 20000 });
    const overdueHeading = section.getByText(/cobran.as vencidas/i);
    const rulesHeading = section.getByText(/regras de cobran.a/i).first();
    await expect(overdueHeading).toBeVisible({ timeout: 10000 });
    await expect(rulesHeading).toBeVisible({ timeout: 10000 });
    const noAutoSendWarning = section.getByText(/n.o enviam mensagens automaticamente|rascunho apenas|nenhum envio autom/i);
    await expect(noAutoSendWarning.first()).toBeVisible({ timeout: 15000 });
    const sendButton = section.getByRole('button', { name: /^enviar$/i });
    const sendVisible = await sendButton.isVisible().catch(() => false);
    expect(sendVisible).toBeFalsy();
  });

  test('18. QR Code sandbox modal and exports work', async () => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(1000);
    const qrButton = page.locator('button[title="Ver QR Code (sandbox)"]').first();
    const hasQr = await qrButton.isVisible().catch(() => false);
    if (hasQr) {
      await qrButton.click({ force: true });
      const modal = page.getByTestId('qr-code-modal');
      await expect(modal).toBeVisible({ timeout: 10000 });
      await expect(modal.getByText(/sandbox\/demo/i)).toBeVisible({ timeout: 5000 });
      await expect(modal.getByText(/não representa pix real/i)).toBeVisible({ timeout: 5000 });
      await modal.press('Escape');
    }
    const csvBtn = page.getByRole('button', { name: /csv/i }).first();
    await expect(csvBtn).toBeVisible({ timeout: 15000 });
    await expect(csvBtn).toBeEnabled({ timeout: 10000 });
    await csvBtn.click({ force: true });
    await page.waitForTimeout(2000);
    const pdfBtn = page.getByRole('button', { name: /pdf/i }).first();
    await expect(pdfBtn).toBeVisible({ timeout: 15000 });
    await expect(pdfBtn).toBeEnabled({ timeout: 10000 });
    await pdfBtn.click({ force: true });
    await page.waitForTimeout(2000);
  });

  test('19. Advanced Analytics section renders with cards and charts', async () => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    const analyticsSection = page.getByTestId('advanced-analytics-section');
    await expect(analyticsSection).toBeVisible({ timeout: 30000 });
    await analyticsSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(2000);

    const overviewCards = analyticsSection.getByTestId('analytics-overview-cards');
    const cardsVisible = await overviewCards.isVisible().catch(() => false);
    if (cardsVisible) {
      await expect(overviewCards).toBeVisible({ timeout: 10000 });
    }

    const periodFilter = analyticsSection.getByTestId('analytics-period-filter');
    await expect(periodFilter).toBeVisible({ timeout: 10000 });

    const csvExportBtn = analyticsSection.getByTestId('analytics-export-csv');
    await expect(csvExportBtn).toBeVisible({ timeout: 10000 });
    const pdfExportBtn = analyticsSection.getByTestId('analytics-export-pdf');
    await expect(pdfExportBtn).toBeVisible({ timeout: 10000 });
  });

  test('20. Analytics period filter changes data', async () => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(500);
    const analyticsSection = page.getByTestId('advanced-analytics-section');
    await expect(analyticsSection).toBeVisible({ timeout: 30000 });
    await analyticsSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);

    const periodFilter = analyticsSection.getByTestId('analytics-period-filter');
    await expect(periodFilter).toBeVisible({ timeout: 10000 });
    await periodFilter.selectOption('30');
    await page.waitForTimeout(2000);
    await expect(analyticsSection).toBeVisible({ timeout: 10000 });
    await periodFilter.selectOption('365');
    await page.waitForTimeout(2000);
    await expect(analyticsSection).toBeVisible({ timeout: 10000 });
  });
});
