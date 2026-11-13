import { test, expect } from '@playwright/test'
import { createHash, randomUUID } from 'node:crypto'
import { PreviewResources } from '../../../src/desktop/preview'

// Exercise the actual host boundary with explicit caller contexts. Native
// Chromium requests and Response bodies are checked separately in the desktop.
function scene() {
  const hooks: Record<string, any> = {}, events: Record<string, any> = {}
  const main: any = { frames: [] }
  const ses: any = { webRequest: {
    onBeforeRequest: (f: any) => { hooks.request = f },
    onBeforeSendHeaders: (f: any) => { hooks.headers = f }
  }, protocol: { handle: (_scheme: string, f: any) => { hooks.serve = f } } }
  const win: any = { isDestroyed: () => false, webContents: { id: 7, isDestroyed: () => false, mainFrame: main, session: ses,
    on: (event: string, f: any) => { events[event] = f } } }
  const host = new PreviewResources(win)
  // Signature-valid transfer; real decoding is covered by actual saved fixtures.
  const png = Buffer.from('89504e470d0a1a0a0102030405', 'hex')
  const value = () => ({ job: 'job', version: 'old', markdown: '[image](assets/a.png)',
    preview: '<img src="slot">', asset_reference_check: { status: 'ok', issues: [] },
    preview_transfer: { job: 'job', version: 'old', slots: [{ start: 10, end: 14, expected: 'slot', key: 'slot' }],
      resources: [{ key: 'slot', asset: 'assets/a.png', representation: 'repr', mime: 'image/png', length: png.length,
        sha256: createHash('sha256').update(png).digest('hex'), base64: png.toString('base64') }] } })
  let nextNode = 10
  const load = (v = value(), generation = randomUUID()) => {
    host.begin(generation)
    const saved = host.prepare(v, 'job', 'old', generation)
    if (saved.preview_lease) host.activate('job', 'old', generation, saved.preview_lease)
    const mount = randomUUID()
    const name = saved.preview_lease ? host.mount(generation, saved.preview_lease, mount) : ''
    const frame: any = { detached: false, name, frameTreeNodeId: nextNode++,
      url: 'about:blank', parent: main }
    main.frames = [frame]
    if (saved.preview_lease) host.bind(generation, saved.preview_lease, mount)
    frame.url = '' // The first image request can precede publication of the srcdoc URL.
    return { saved, frame, url: saved.preview.match(/src="([^"]+)"/)?.[1], generation, mount }
  }
  const ask = (url: string, frame: any, extra = {}) => ({ url, frame, method: 'GET', webContentsId: 7, resourceType: 'image', ...extra })
  const check = (details: any) => { let result: any; hooks.request(details, (v: any) => { result = v }); return result }
  const serve = async (details: any) => {
    let result: any
    hooks.headers({ ...details, requestHeaders: {} }, (v: any) => { result = v })
    if (result.cancel) return 403
    return hooks.serve(new Request(details.url, { headers: result.requestHeaders }))
  }
  return { host, hooks, events, main, value, load, ask, check, serve, png, win }
}

test('only issued resources in the owning live frame cross the host request boundary', async () => {
  const s = scene(), { url, frame } = s.load()
  const response = await s.serve(s.ask(url, frame))
  expect(response).toBeInstanceOf(Response)
  expect(Buffer.from(await response.arrayBuffer())).toEqual(s.png)
  expect(response.headers.get('cache-control')).toBe('no-store')
  expect(response.headers.get('x-content-type-options')).toBe('nosniff')
  for (const details of [s.ask(url, null), s.ask(url, undefined), s.ask(url, frame, { webContentsId: 8 }),
    s.ask(url, s.main, { resourceType: 'mainFrame' }), s.ask(url, frame, { resourceType: 'xhr' }),
    s.ask(url, { ...frame, name: 'unrelated', frameTreeNodeId: 11 }),
    s.ask(url, frame, { method: 'POST' }),
    ...['?q=1', '#fragment', '/extra', '%2F'].map(suffix => s.ask(url + suffix, frame)),
    s.ask(url.replace('/snapshot/', '/foreign/'), frame)]) {
    expect(s.check(details).cancel).toBe(true)
  }
  // An opaque origin, referrer or manually constructed Request supplies no grant.
  expect((await s.hooks.serve(new Request(url, { headers: { Origin: 'null', Referer: url } }))).status).toBe(403)
  let prevented = false
  s.events['will-redirect']({ preventDefault: () => { prevented = true } })
  expect(prevented).toBe(true)
  s.host.release()
  expect(s.check(s.ask(url, frame)).cancel).toBe(true)
})

test('new selection and same-pair retry revoke old grants and reject late activation', async () => {
  const s = scene(), old = s.load()
  let headers: any
  s.hooks.headers({ ...s.ask(old.url, old.frame), requestHeaders: {} }, (r: any) => { headers = r.requestHeaders })
  const current = s.load()
  expect(() => s.host.activate('job', 'old', old.generation, old.saved.preview_lease)).toThrow('Obsolete')
  expect(() => s.host.bind(old.generation, old.saved.preview_lease, old.mount)).toThrow('Obsolete')
  s.host.unmount(old.generation, old.saved.preview_lease, old.mount)
  expect((await s.hooks.serve(new Request(old.url, { headers }))).status).toBe(403)
  s.host.release(old.generation) // Late old cleanup must not revoke the new load.
  expect(s.check(s.ask(current.url, current.frame)).cancel).toBe(false)
  expect(() => s.host.prepare(s.value(), 'job', 'old', old.generation)).toThrow('Obsolete')
  s.events['render-process-gone']()
  expect(s.check(s.ask(current.url, current.frame)).cancel).toBe(true)
})

test('Return and tab remounts register a fresh frame without replacing the loaded resource table', async () => {
  const s = scene(), old = s.load(), mount = randomUUID()
  const name = s.host.mount(old.generation, old.saved.preview_lease, mount)
  const frame = { ...old.frame, name, frameTreeNodeId: 11, url: 'about:blank' }
  s.main.frames.push(frame) // The retiring frame can still exist during remount.
  expect(s.check(s.ask(old.url, old.frame)).cancel).toBe(true)
  expect(s.check(s.ask(old.url, frame)).cancel).toBe(true)
  expect(await s.serve(s.ask(old.url, frame))).toBe(403)
  expect(() => s.host.bind(old.generation, old.saved.preview_lease, old.mount)).toThrow('Obsolete')
  s.host.bind(old.generation, old.saved.preview_lease, mount)
  frame.url = ''
  expect(s.check(s.ask(old.url, frame)).cancel).toBe(false)
  expect(s.check(s.ask(old.url, { ...frame, frameTreeNodeId: 12 })).cancel).toBe(true)
  s.host.unmount(old.generation, old.saved.preview_lease, old.mount)
  const response = await s.serve(s.ask(old.url, frame))
  expect(Buffer.from(await response.arrayBuffer())).toEqual(s.png)
  s.host.unmount(old.generation, old.saved.preview_lease, mount)
  expect(s.check(s.ask(old.url, frame)).cancel).toBe(true)
})

test('registration requires one attached direct child at the inert URL', () => {
  const s = scene(), { generation, saved, frame, url } = s.load(), mount = randomUUID()
  const name = s.host.mount(generation, saved.preview_lease, mount)
  const child = { ...frame, name, frameTreeNodeId: 11, url: 'about:blank' }
  const bind = () => s.host.bind(generation, saved.preview_lease, mount)
  for (const children of [[], [{ ...child, detached: true }], [{ ...child, parent: frame }],
    [{ ...child, url: 'about:srcdoc' }], [child, { ...child, frameTreeNodeId: 12 }]]) {
    s.main.frames = children
    expect(bind).toThrow('Could not identify the inert preview frame')
    expect(s.check(s.ask(url, child)).cancel).toBe(true)
  }
  s.main.frames = [child]
  bind()
  expect(s.check(s.ask(url, child)).cancel).toBe(false)
  const replacement = { ...child, frameTreeNodeId: 13 }
  s.main.frames = [replacement]
  expect(bind).toThrow('Obsolete')
  expect(s.check(s.ask(url, replacement)).cancel).toBe(true)
  expect(s.check(s.ask(url, child)).cancel).toBe(true)
})

test('late requests after window destruction fail without accessing destroyed native objects', async () => {
  const s = scene(), loaded = s.load()
  s.events['render-process-gone']()
  Object.defineProperty(s.win.webContents, 'mainFrame', { get: () => { throw new Error('Render frame was disposed') } })
  expect(s.check(s.ask('file:///unavailable', loaded.frame)).cancel).toBe(true)
  s.events.destroyed()
  s.win.isDestroyed = () => true
  Object.defineProperty(s.win, 'webContents', { get: () => { throw new Error('Object has been destroyed') } })
  expect(s.check(s.ask(loaded.url, loaded.frame)).cancel).toBe(true)
  expect(s.check(s.ask('file:///unavailable', loaded.frame)).cancel).toBe(true)
  expect(await s.serve(s.ask(loaded.url, loaded.frame))).toBe(403)
})

test('payload, binding and preparation failures publish no partial resource table and preserve raw data', async () => {
  for (const mutate of [
    (v: any) => { v.preview_transfer.resources[0].length++ },
    (v: any) => { v.preview_transfer.resources[0].sha256 = '0'.repeat(64) },
    (v: any) => { v.preview_transfer.resources[0].mime = 'image/jpeg' },
    (v: any) => { v.preview_transfer.slots[0].expected = 'other' },
    (v: any) => { v.preview_transfer.resources.push({ ...v.preview_transfer.resources[0] }) },
    (v: any) => { v.preview_transfer.resources[0].base64 = null }
  ]) {
    const s = scene(), old = s.load(), value = s.value()
    mutate(value)
    const current = s.load(value)
    expect(current.saved.preview_error).toContain('Preview unavailable')
    expect(current.saved.markdown).toBe(value.markdown)
    expect(current.saved.asset_reference_check).toEqual(value.asset_reference_check)
    expect(current.saved.preview_transfer).toBeUndefined()
    expect(s.check(s.ask(old.url, old.frame)).cancel).toBe(true)
    expect(() => s.host.activate('job', 'old', current.generation, 'invalid')).toThrow('Obsolete')
  }
})
