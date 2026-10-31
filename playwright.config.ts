import { defineConfig } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'

// Results may be cleared by Playwright; durable case evidence is a sibling directory.
const testRunRoot = resolve(process.env.PDFMD_TEST_RUN_ROOT ||
  `.local/test-runs/${new Date().toISOString().replace(/\D/g, '')}-${process.pid}`)
process.env.PDFMD_TEST_RUN_ROOT = testRunRoot
mkdirSync(testRunRoot, { recursive: true })

export default defineConfig({
  testDir: './tests/desktop/specs', outputDir: resolve(testRunRoot, 'results'),
  timeout: 120000, workers: 1,
  use: { trace: 'retain-on-failure' }, reporter: 'list'
})
