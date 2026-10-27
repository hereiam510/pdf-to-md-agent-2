import { test, expect, _electron as electron } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { execFileSync } from 'node:child_process'

for (const protocol of ['chat_completions', 'responses']) {
  test(`stream wait defaults and explicit future settings survive reopen: ${protocol}`, async () => {
    const directory = await fs.mkdtemp(resolve('.local/stream-settings-desktop-'))
    const workspace = join(directory, 'workspace'), source = join(directory, 'Waiting settings source.pdf')
    const python = resolve('.venv/Scripts/python.exe')
    execFileSync(python, ['tools/make-smoke-pdf.py', source], { windowsHide: true })
    const fixture = JSON.parse(execFileSync(python, ['-c', `
import json,sys
from pathlib import Path
from pdfmd.storage import Store
from pdfmd.evidence import Evidence
from pdfmd.nexus import Nexus
s=Store(Path(sys.argv[1]))
protocol=sys.argv[3]
route={"endpoint":"http://127.0.0.1:9/v1/"+("responses" if protocol=="responses" else "chat/completions"),"model":"offline-only","protocol":protocol,"context_tokens":65536,"output_tokens":2048}
j=Evidence(s).create_job(sys.argv[2],"Preserve the complete source.",route)
j=s.update_job(j["id"],attempts=3,active_seconds=17)
r=Nexus(s,lambda _: "must-not-be-used").freeze(j["id"],"existing-frozen",{"stream":False,"original":"preserved"},"compaction",{})
print(json.dumps({"job":j,"request":r}))
`, workspace, source, protocol], { windowsHide: true, encoding: 'utf-8' }))
    const launch = () => electron.launch({ args: [resolve('out/main/index.js')], env: { ...process.env,
      PDFMD_DATA: workspace, PDFMD_PYTHON: python } })
    let app = await launch()
    try {
      let page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.getByRole('button', { name: 'Nexus connection' }).click()
      await expect(page.getByLabel('Response waiting', { exact: true })).toHaveValue('streaming')
      await expect(page.getByLabel('First progress wait (seconds)', { exact: true })).toHaveValue('600')
      await expect(page.getByLabel('Progress idle wait (seconds)', { exact: true })).toHaveValue('300')
      const total = page.getByLabel('Set a total request deadline', { exact: true })
      await expect(total).not.toBeChecked()
      await expect(page.getByLabel('Total request deadline (seconds)', { exact: true })).toHaveCount(0)
      await page.getByRole('combobox', { name: 'Protocol', exact: true }).selectOption(protocol)
      await page.getByLabel('Full endpoint URL', { exact: true }).fill(fixture.job.route.endpoint)
      await page.getByLabel('Model alias', { exact: true }).fill('offline-only')
      await total.check()
      await page.getByLabel('Total request deadline (seconds)', { exact: true }).fill('1200')
      await expect(page.getByText('This optional deadline stops the request even if generation is still progressing.')).toBeVisible()
      await total.uncheck()
      await page.screenshot({ path: join(directory, 'new-connection-progress-default.png') })
      await page.getByRole('button', { name: 'Save connection', exact: true }).click()
      const connection = await page.evaluate(() => window.workbench.invoke('settings'))
      expect(connection.route.wait_policy).toEqual({ first_progress_seconds: 600, idle_progress_seconds: 300, total_seconds: null })
      await page.locator('.document-item').first().click()
      await page.getByRole('button', { name: 'Task limits', exact: true }).click()
      await expect(page.getByLabel('Response waiting', { exact: true })).toHaveValue('complete')
      await expect(page.getByLabel('Request deadline (seconds)', { exact: true })).toHaveValue('180')
      await page.getByLabel('Response waiting', { exact: true }).selectOption('streaming')
      await expect(page.getByLabel('Set a total request deadline', { exact: true })).not.toBeChecked()
      await page.getByLabel('First progress wait (seconds)', { exact: true }).fill('700')
      await page.getByLabel('Progress idle wait (seconds)', { exact: true }).fill('350')
      await page.getByRole('button', { name: 'Save task limits', exact: true }).click()
      await expect(page.getByRole('form', { name: 'Task limits', exact: true })).toBeHidden()
      const changed = await page.evaluate(job => window.workbench.invoke('job', { job }), fixture.job.id)
      expect(changed.route.wait_policy).toEqual({ first_progress_seconds: 700, idle_progress_seconds: 350, total_seconds: null })
      expect(changed.attempts).toBe(3)
      expect(changed.active_seconds).toBe(17)
      expect(changed.requests).toHaveLength(1)
      expect(changed.requests[0].route).toEqual(fixture.request.route)
      await app.close(); app = await launch(); page = await app.firstWindow()
      await expect(page.getByText('Local engine ready')).toBeVisible({ timeout: 60000 })
      await page.locator('.document-item').first().click()
      await page.getByRole('button', { name: 'Task limits', exact: true }).click()
      await expect(page.getByLabel('Response waiting', { exact: true })).toHaveValue('streaming')
      await expect(page.getByLabel('First progress wait (seconds)', { exact: true })).toHaveValue('700')
      await expect(page.getByLabel('Progress idle wait (seconds)', { exact: true })).toHaveValue('350')
      await expect(page.getByLabel('Set a total request deadline', { exact: true })).not.toBeChecked()
      await page.screenshot({ path: join(directory, 'reopened-task-policy.png') })
      await page.getByLabel('Set a total request deadline', { exact: true }).check()
      await page.getByLabel('Total request deadline (seconds)', { exact: true }).fill('1500')
      await page.getByRole('button', { name: 'Save task limits', exact: true }).click()
      await expect(page.getByRole('form', { name: 'Task limits', exact: true })).toBeHidden()
      const capped = await page.evaluate(job => window.workbench.invoke('job', { job }), fixture.job.id)
      expect(capped.route.wait_policy.total_seconds).toBe(1500)
      await page.getByRole('button', { name: 'Dismiss notice', exact: true }).click()
      await page.getByRole('button', { name: 'Task limits', exact: true }).click()
      await page.getByLabel('Set a total request deadline', { exact: true }).uncheck()
      await page.getByRole('button', { name: 'Save task limits', exact: true }).click()
      await expect(page.getByRole('form', { name: 'Task limits', exact: true })).toBeHidden()
      const verified = JSON.parse(execFileSync(python, ['-c', `
import json,sys
from pathlib import Path
from pdfmd.storage import Store
s=Store(Path(sys.argv[1]));j=s.get("job",sys.argv[2]);r=s.get("request","existing-frozen")
assert not s.records("attempt",j["id"])
assert j["attempts"]==3 and j["active_seconds"]==17
assert s.json(r["payload_ref"],j["id"])=={"stream":False,"original":"preserved"}
assert j["route"]["wait_policy"]=={"first_progress_seconds":700,"idle_progress_seconds":350,"total_seconds":None}
print(json.dumps({"job":j,"request":r,"settings":s.records("task_settings",j["id"]),"attempt_records":0,"live_model_calls":0}))
`, workspace, fixture.job.id], { windowsHide: true, encoding: 'utf-8' }))
      expect(verified.request).toEqual(fixture.request)
      expect(verified.settings).toHaveLength(3)
      await fs.writeFile(join(directory, 'verification.json'), JSON.stringify({ protocol, fixture, connection, changed, capped, verified }, null, 2))
    } finally { await app.close() }
  })
}
