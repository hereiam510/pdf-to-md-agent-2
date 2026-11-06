import { test, expect, _electron as electron } from '@playwright/test'
import { promises as fs } from 'node:fs'
import { resolve, join } from 'node:path'
import { testRunRoot } from '../support/artifacts'

test('development startup loads the selected credential without changing settings, leaking it or sending requests', async () => {
  const directory = await fs.mkdtemp(resolve(testRunRoot, 'credential-'))
  const workspace = join(directory, 'workspace')
  const file = join(directory, 'key.txt')
  const secret = 'synthetic-private-credential-for-startup-test'
  const route = { endpoint:'http://127.0.0.1:1/v1/chat/completions', model:'synthetic-no-provider', protocol:'chat_completions',
    context_tokens:131072, output_tokens:8192, image_tokens:4096, estimation_profile:'bpe_proxy_v1', vision:true,
    timeout_seconds:180, wait_policy:null, parameters:{reasoning_effort:'low'} }
  const limits = {max_requests:12,max_active_seconds:1200,max_response_repairs:2,replay_unknown:false,max_attempts_per_request:1}
  await fs.mkdir(workspace, {recursive:true})
  const connection = join(directory, 'connection.json')
  const original = JSON.stringify({route,limits,remember:false},null,2)
  await fs.writeFile(connection, original)
  await fs.writeFile(file,secret+'\r\n')
  const launch = (name:string, skip=false) => electron.launch({args:[resolve('tests/desktop/support/isolated-workbench.cjs')],
    env:{...process.env,PDFMD_UI_PROFILE:join(directory,name),PDFMD_DATA:workspace,
      PDFMD_PYTHON:resolve('.venv/Scripts/python.exe'),PDFMD_CREDENTIAL_FILE:file,PDFMD_SKIP_CREDENTIAL_FILE:skip?'1':'0'}})
  for (const [stage, skip, invalid] of [['loaded',false,false],['reopened',false,false],['disabled',true,false],['invalid',false,true]] as const) {
    if (invalid) await fs.writeFile(file,' \n')
    const app = await launch(stage,skip)
    const logs:string[] = []
    app.process().stdout?.on('data',chunk=>logs.push(String(chunk)))
    app.process().stderr?.on('data',chunk=>logs.push(String(chunk)))
    try {
      const page = await app.firstWindow()
      if (invalid) await expect(page.locator('body')).toContainText('Cannot load the development credential file',{timeout:30000})
      else await expect(page.getByText('Local engine ready')).toBeVisible({timeout:30000})
      const settings = await page.evaluate(() => (window as any).workbench.invoke('settings'))
      expect(settings).toMatchObject({route,limits,remember:false,hasKey:!skip&&!invalid})
      expect(JSON.stringify(settings)+logs.join('')+await page.locator('body').innerText()).not.toContain(secret)
      if (!invalid) expect(await page.evaluate(() => (window as any).workbench.invoke('jobs'))).toEqual([])
      expect(await fs.readFile(connection,'utf8')).toBe(original)
    } finally { await app.close() }
  }
})
