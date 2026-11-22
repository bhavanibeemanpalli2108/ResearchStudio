import { test, expect } from '@playwright/test';

test('literature selection reaches native ideation with retained source provenance', async ({
  page,
}) => {
  test.skip(process.env.NATIVE_OFFLINE_E2E !== '1', 'Requires the mock-literature offline fixture');
  await page.goto('/literature');
  await page.getByLabel('Research topic or DOI').fill('scheduling');
  await page.getByRole('button', { name: 'Search literature', exact: true }).click();
  await expect(
    page.getByRole('heading', { name: 'A real metadata record', exact: true }),
  ).toBeVisible();
  await page.getByRole('checkbox', { name: 'Select A real metadata record', exact: true }).check();
  await page.getByRole('link', { name: 'Use selected papers in research' }).click();
  await expect(page.getByText('A real metadata record', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Use example', exact: true }).click();
  await page
    .getByLabel(/Research question/)
    .fill('Does the proposed algorithm improve its approved baseline?');
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Continue', exact: true }).click();
  await page.getByRole('button', { name: 'Launch research', exact: true }).click();
  await expect(page).toHaveURL(/workspace\//);
  const id = page.url().split('/').pop();
  await page
    .getByRole('button', { name: 'Review proposal', exact: true })
    .click({ timeout: 60000 });
  await page.getByRole('dialog').getByRole('button', { name: 'Approve & continue' }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page
    .getByRole('button', { name: 'Review proposal', exact: true })
    .click({ timeout: 60000 });
  const run = await (await page.request.get(`/api/runs/${id}`)).json();
  expect(run.approval.gate).toBe('approval');
  expect(run.config.selected_literature[0].provenance.length).toBe(2);
  expect(run.state.literature[0].title).toBe('A real metadata record');
  expect(run.state.literature[0].selection).toBe('explicit_user_selection');
  expect(await (await page.request.get(`/api/runs/${id}/experiments`)).json()).toEqual([]);
  await page.request.post(`/api/runs/${id}/cancel`);
});
