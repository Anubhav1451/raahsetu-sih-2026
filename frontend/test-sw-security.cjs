const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const handlers = {};
const deleted = [];
vm.runInNewContext(readFileSync(__dirname + '/public/sw.js', 'utf8'), {
  self: {location: {origin: 'https://example.test'}, addEventListener: (name, fn) => handlers[name] = fn, clients: {claim() {}}, skipWaiting() {}},
  URL, Response,
  caches: {keys: async () => ['raahsetu-shell-v1', 'raahsetu-shell-v2', 'other-app'], delete: async key => deleted.push(key)},
});
for (const [path, auth] of [['/api/v1/me',false], ['/api/v1/deliveries',false], ['/assets/app.js',true], ['/index.html?token=secret',false], ['/private.json',false]]) {
  handlers.fetch({request: {method:'GET', url:'https://example.test'+path, headers: new Headers(auth ? {Authorization:'Bearer test'} : {})}, respondWith() {throw Error('Private request intercepted: '+path);}});
}
let done;
handlers.activate({waitUntil(promise) {done=promise;}});
done.then(()=>{assert.deepEqual(deleted,['raahsetu-shell-v1']); console.log('PASS: private/API requests bypass cache; only obsolete app caches deleted');}).catch(error=>{console.error(error);process.exitCode=1});
