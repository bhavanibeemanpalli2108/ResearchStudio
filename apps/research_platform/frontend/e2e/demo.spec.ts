import { test, expect } from '@playwright/test';
test('demo research moves through both human approval gates to fixture evidence and paper', async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/create?profile=demo');
  await page.getByRole('button', { name: 'Use example' }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await expect(page.getByRole('radio', { name: /Full research/ })).toBeDisabled();
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
  await expect(page.locator('.paper-document')).toContainText(/circle|packing/i);
  await expect(page.locator('.paper-document table')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Markdown', exact: true })).toBeEnabled();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Markdown', exact: true }).click();
  const reportDownload = await downloadPromise;
  await reportDownload.saveAs(testInfo.outputPath('demo-report.md'));
  await page.screenshot({ path: testInfo.outputPath('completed-demo.png'), fullPage: true });
  await testInfo.attach('completed-run', {
    body: JSON.stringify({ url: page.url(), report: reportDownload.suggestedFilename() }),
    contentType: 'application/json',
  });
  expect(errors).toEqual([]);
});

test('paused demo resumes and cancellation persists after refresh', async ({ page }, testInfo) => {
  const projectResponse = await page.request.post('/api/projects', {
    data: {
      title: 'Browser control validation',
      question: 'How do the reviewed demo circle packing configurations compare?',
      domain: 'Optimization',
      objectives: [],
      references: [],
    },
  });
  expect(projectResponse.ok()).toBe(true);
  const project = (await projectResponse.json()) as { id: string };
  const runResponse = await page.request.post(`/api/projects/${project.id}/runs`, {
    data: {
      execution_protocol: 2,
      engine: 'native',
      profile: 'demo',
      provider: 'mock',
      model: 'mock-researcher',
      require_approval: true,
    },
  });
  expect(runResponse.ok()).toBe(true);
  const run = (await runResponse.json()) as { id: string };
  expect((await page.request.post(`/api/runs/${run.id}/pause`)).ok()).toBe(true);
  await page.goto(`/workspace/${run.id}`);
  await expect(page.locator('.run-statusbar .badge').first()).toHaveText('Paused');
  await page.getByRole('button', { name: 'Resume', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Review proposal', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel run', exact: true }).click();
  await expect(page.locator('.run-statusbar .badge').first()).toHaveText('Cancelled');
  await page.reload();
  await expect(page.locator('.run-statusbar .badge').first()).toHaveText('Cancelled');
  await testInfo.attach('cancelled-run', {
    body: JSON.stringify({ id: run.id, status: 'cancelled' }),
    contentType: 'application/json',
  });
});
test('mobile navigation and theme remain accessible', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('link', { name: 'Research projects' })
    .click();
  await expect(page).toHaveURL('/history');
  await page.getByRole('button', { name: /Switch to light theme/ }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  expect(await page.locator('body').evaluate((el) => el.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});
test('paper editor loads its local assets and keeps edits as a browser draft', async ({ page }) => {
  const runs = (await (await page.request.get('/api/runs')).json()) as {
    id: string;
    status: string;
  }[];
  const run = runs.find((item) => item.status === 'completed');
  expect(run).toBeTruthy();
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/paper/' + run!.id);
  await page.getByRole('button', { name: 'Edit markdown', exact: true }).click();
  const editor = page.locator('.monaco-editor').first();
  await expect(editor).toBeVisible({ timeout: 30000 });
  await editor.click();
  await page.keyboard.press('Control+End');
  await page.keyboard.type('\n\nLocal draft review note.');
  await expect(page.getByText('Local draft', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Preview', exact: true }).click();
  await expect(page.locator('.paper-document')).toContainText('Local draft review note.');
  await page.reload();
  await expect(page.locator('.paper-document')).toContainText('Local draft review note.');
  await page.getByRole('button', { name: 'Edit markdown', exact: true }).click();
  await expect(page.locator('.monaco-editor').first()).toBeVisible();
  await page.getByRole('button', { name: 'Reset to generated paper', exact: true }).click();
  await expect(page.getByText('Local draft', { exact: true })).not.toBeVisible();
  await page.getByRole('button', { name: 'Preview', exact: true }).click();
  await expect(page.locator('.paper-document')).not.toContainText('Local draft review note.');
  expect(errors).toEqual([]);
});
