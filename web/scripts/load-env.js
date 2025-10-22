#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// Read environment variables from process.env
const envVars = {
  NEXT_PUBLIC_SERVER_URL: process.env.NEXT_PUBLIC_SERVER_URL || '',
  NEXT_PUBLIC_API_PORT: process.env.NEXT_PUBLIC_API_PORT || '',
  NEXT_PUBLIC_UI_PORT: process.env.NEXT_PUBLIC_UI_PORT || ''
};

// Create the runtime config
const runtimeConfig = `
window.__ENV__ = ${JSON.stringify(envVars, null, 2)};
`;

// Write to public directory
const publicDir = path.join(__dirname, '..', 'public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

fs.writeFileSync(path.join(publicDir, 'env.js'), runtimeConfig);
console.log('Runtime environment variables written to /public/env.js');