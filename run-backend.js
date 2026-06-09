const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const isWin = process.platform === 'win32';
const venvPath = path.join(__dirname, '.venv');
let uvicornCmd = 'uvicorn';

if (fs.existsSync(venvPath)) {
  const localUvicorn = isWin 
    ? path.join(venvPath, 'Scripts', 'uvicorn.exe')
    : path.join(venvPath, 'bin', 'uvicorn');
  
  if (fs.existsSync(localUvicorn)) {
    uvicornCmd = localUvicorn;
  }
}

console.log(`[Backend] Starting server with command: ${uvicornCmd}`);
const child = spawn(uvicornCmd, ['app.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'], {
  stdio: 'inherit',
  shell: true
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
