// Build the browser-only demo: replay fixtures, no backend.
//   BASE_PATH=/IIoT-Telemetry-Stack npm run build:demo
import { spawnSync } from 'node:child_process';
import { cpSync, existsSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const out = join(root, 'build-demo');
const fixtures = join(root, 'demo-fixtures');

if (!existsSync(join(fixtures, 'manifest.json'))) {
	console.error('demo-fixtures/manifest.json missing - run tools/make_placeholder_demo_fixtures.py or capture_demo_fixtures.py');
	process.exit(1);
}
rmSync(out, { recursive: true, force: true });
const r = spawnSync('npx', ['vite', 'build'], {
	cwd: root,
	stdio: 'inherit',
	shell: true,
	env: { ...process.env, VITE_DEMO_MODE: 'true' },
});
if (r.status !== 0) process.exit(r.status ?? 1);
cpSync(fixtures, join(out, 'demo-fixtures'), { recursive: true });
console.log('demo build ->', out);
