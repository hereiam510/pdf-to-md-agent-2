const { createWorker } = require('tesseract.js')
const fs = require('node:fs')
const [input, languages, output, cachePath] = process.argv.slice(2)
;(async () => {
  fs.mkdirSync(cachePath, { recursive: true })
  const worker = await createWorker(languages, 1, {
    cachePath,
    logger: (event) => process.stderr.write(JSON.stringify(event) + '\n')
  })
  try {
    const { data } = await worker.recognize(input, {}, { text: true, blocks: true, hocr: true, tsv: true })
    fs.writeFileSync(output, JSON.stringify(data), { encoding: 'utf8', flag: 'wx' })
  } finally {
    await worker.terminate()
  }
})().catch((error) => { process.stderr.write(String(error) + '\n'); process.exitCode = 1 })
