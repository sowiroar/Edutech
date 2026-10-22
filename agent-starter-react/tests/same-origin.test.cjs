const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

function loadSameOrigin(env = {}) {
  const context = {
    exports: {},
    process: { env },
    URL,
    require: (name) => {
      if (name === 'node:crypto') return require(name);
      if (name === 'next/headers' || name === 'jose') return {};
      throw new Error(`Unexpected dependency: ${name}`);
    },
  };
  const source = fs.readFileSync(path.join(__dirname, '../lib/telemetry/server.ts'), 'utf8');
  vm.runInNewContext(
    ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    context
  );
  return context.exports.sameOrigin;
}

function request(origin, url = 'http://0.0.0.0:3000/api/token') {
  return new Request(url, { headers: origin === undefined ? {} : { origin } });
}

test('accepts the canonical external origin behind a container proxy', () => {
  const sameOrigin = loadSameOrigin({ TELEMETRY_PUBLIC_ORIGIN: 'http://localhost:3500' });
  assert.equal(sameOrigin(request('http://localhost:3500')), true);
  assert.equal(sameOrigin(request('http://localhost:3000')), false);
});

test('accepts only explicitly configured aliases, with whitespace trimmed', () => {
  const sameOrigin = loadSameOrigin({
    TELEMETRY_PUBLIC_ORIGIN: 'http://localhost:3500',
    TELEMETRY_ADDITIONAL_ORIGINS: ' http://localhost:3000 , https://demo.example.org ',
  });
  assert.equal(sameOrigin(request('http://localhost:3000')), true);
  assert.equal(sameOrigin(request('https://demo.example.org')), true);
  for (const origin of [
    undefined,
    'null',
    'https://evil.example',
    'http://localhost:3000.evil.example',
    'http://localhost:3001',
    'https://localhost:3000',
  ]) {
    assert.equal(sameOrigin(request(origin)), false, `must reject ${origin}`);
  }
});

test('preserves same-origin requests without proxy configuration', () => {
  const sameOrigin = loadSameOrigin();
  assert.equal(sameOrigin(request('https://app.example.org', 'https://app.example.org/api/token')), true);
  assert.equal(sameOrigin(request(undefined)), false);
  assert.equal(sameOrigin(request('null')), false);
});
