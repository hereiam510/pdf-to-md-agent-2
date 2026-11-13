import { resolve } from 'node:path'

// playwright.config.ts creates this once and passes the identity to every worker.
export const testRunRoot = resolve(process.env.PDFMD_TEST_RUN_ROOT || '.local/test-runs/manual')
