#!/usr/bin/env node
/**
 * Cross-platform launcher: runs `python -m <args>` from backend/.venv.
 * Usage: node scripts/run-backend.cjs <module> [args...]
 *   e.g. node scripts/run-backend.cjs uvicorn app.main:app --port 8765
 */
const { spawn } = require('node:child_process')
const path = require('node:path')
const fs = require('node:fs')

const isWin = process.platform === 'win32'
const repo = path.resolve(__dirname, '..')
const venv = path.join(repo, 'backend', '.venv')
const py = isWin
  ? path.join(venv, 'Scripts', 'python.exe')
  : path.join(venv, 'bin', 'python')

if (!fs.existsSync(py)) {
  console.error(`Python venv not found at ${py}`)
  console.error('Run `npm run install:all` first.')
  process.exit(1)
}

const args = ['-m', ...process.argv.slice(2)]
const child = spawn(py, args, {
  cwd: path.join(repo, 'backend'),
  stdio: 'inherit',
})
child.on('exit', (code, signal) => {
  process.exit(code ?? (signal ? 1 : 0))
})
