import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('./src/api.ts', import.meta.url), 'utf8')
  .replace('import.meta.env.VITE_API_BASE_URL', 'undefined');
const output = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const api = await import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`);
let configAttempts = 0;
let failAuth = false;
globalThis.fetch = async (url, init) => {
  if (url === '/api/v1/public-config') {
    configAttempts++;
    return new Response(JSON.stringify(configAttempts === 1
      ? { detail: 'temporary failure' }
      : { supabase_url: 'https://example.invalid', supabase_publishable_key: 'test-public' }),
    { status: configAttempts === 1 ? 503 : 200 });
  }
  assert.equal(url, 'https://example.invalid/auth/v1/token?grant_type=refresh_token');
  assert.equal(JSON.parse(init.body).refresh_token, 'test-refresh');
  assert.ok(init.signal);
  return new Response(JSON.stringify(failAuth
    ? { msg: 'expired refresh token' }
    : { access_token: 'test-access', refresh_token: 'rotated', expires_in: 3600 }),
  { status: failAuth ? 400 : 200 });
};
await assert.rejects(api.refreshSession('test-refresh'), /temporary failure/);
const renewed = await api.refreshSession('test-refresh');
assert.equal(configAttempts, 2);
assert.equal(renewed.refresh_token, 'rotated');
assert.ok(renewed.expires_at > Date.now() / 1000);
failAuth = true;
await assert.rejects(api.refreshSession('test-refresh'), (error) =>
  error instanceof api.AuthError && error.status === 400);
console.log('PASS: configuration retry, refresh request, rotation, expiry and invalid-session errors');
