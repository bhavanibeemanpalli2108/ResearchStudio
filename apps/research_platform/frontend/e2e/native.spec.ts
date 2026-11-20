import { test, expect } from '@playwright/test';

test('native approvals lead to retained measurements and consistent final report with mock Groq', async ({
  page,
}, testInfo) => {
  test.skip(
    process.env.NATIVE_OFFLINE_E2E !== '1',
    'Requires the explicit offline native fixture server',
  );
  await page.goto('/create?profile=free_research');
  await page.getByRole('button', { name: 'Use example' }).click();
  await page
    .getByLabel(/Research question/)
    .fill('Does the proposed algorithm improve its approved baseline?');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Provider', exact: true })).toHaveValue('groq');
  await expect(page.getByRole('combobox', { name: 'Model', exact: true })).toHaveValue(
    'openai/gpt-oss-20b',
  );
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Launch research' }).click();
  await expect(page).toHaveURL(/\/workspace\//);
  for (let gate = 0; gate < 2; gate++) {
    await page
      .getByRole('button', { name: 'Review proposal', exact: true })
      .click({ timeout: 60000 });
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Approve & continue' }).click();
    await expect(dialog).not.toBeVisible();
  }
  await expect(page.locator('.run-statusbar .badge').first()).toHaveText('Completed', {
    timeout: 90000,
  });
  const tabs = page.getByRole('navigation', { name: 'Research run views' });
  await tabs.getByRole('link', { name: /Experiments/ }).click();
  await expect(page.getByText('Experiment 01', { exact: true })).toBeVisible();
  await tabs.getByRole('link', { name: 'Paper & artifacts' }).click();
  await expect(page.locator('.paper-document')).toContainText('AI-generated');
  await expect(page.locator('.paper-document')).toContainText('Final approved experiment contract');
  await expect(page.locator('.paper-document')).toContainText('Historical proposals');
  const runId = page.url().match(/(?:workspace|paper)\/([a-f0-9]+)/)?.[1];
  expect(runId).toBeTruthy();
  const report = await (await page.request.get(`/api/runs/${runId}/report`)).json();
  expect(report.derived).toBe(true);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Markdown', exact: true }).click();
  const saved = testInfo.outputPath('offline-native-report.md');
  await (await download).saveAs(saved);
  const { readFile } = await import('node:fs/promises');
  expect(await readFile(saved, 'utf-8')).toBe(report.markdown);
  await page.screenshot({
    path: testInfo.outputPath('offline-native-completed.png'),
    fullPage: true,
  });
});
