// Use the actual built app with a private Electron profile for this local test.
const { app } = require('electron')
const { mkdirSync } = require('node:fs')
const { resolve } = require('node:path')
const profile = process.env.PDFMD_UI_PROFILE
if (!profile) throw new Error('A private test profile is required.')
mkdirSync(profile, { recursive: true })
app.setPath('userData', resolve(profile))
require(resolve('out/main/index.js'))
