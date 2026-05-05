#!/usr/bin/env node
/** One-shot installer: backend venv + pip + frontend npm. Cross-platform. */
const { spawnSync } = require('node:child_process')
const path = require('node:path')
const fs = require('node:fs')

const isWin = process.platform === 'win32'
const repo = path.resolve(__dirname, '..')
const backend = path.join(repo, 'backend')
const frontend = path.join(repo, 'frontend')
const venv = path.join(backend, '.venv')
const py = isWin
  ? path.join(venv, 'Scripts', 'python.exe')
  : path.join(venv, 'bin', 'python')

function run(cmd, args, opts = {}) {
  const label = `> ${cmd} ${args.join(' ')}`
  console.log(`\n${label}`)
  const res = spawnSync(cmd, args, { stdio: 'inherit', shell: false, ...opts })
  if (res.status !== 0) {
    console.error(`Command failed (exit ${res.status})`)
    process.exit(res.status ?? 1)
  }
}

// 1. Create venv if missing
if (!fs.existsSync(py)) {
  console.log('Creating backend Python venv…')
  run('python', ['-m', 'venv', '.venv'], { cwd: backend })
}

// 2. Install backend deps
run(py, ['-m', 'pip', 'install', '--upgrade', 'pip'], { cwd: backend })
run(py, ['-m', 'pip', 'install', '-r', 'requirements.txt'], { cwd: backend })

// 3. Install frontend deps
run(isWin ? 'npm.cmd' : 'npm', ['install'], { cwd: frontend })

console.log('\n✓ All dependencies installed. Run `npm run dev` to start.')
