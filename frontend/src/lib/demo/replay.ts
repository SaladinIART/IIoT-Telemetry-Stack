/**
 * Browser-only replay of NEXUS API output (VITE_DEMO_MODE=true).
 *
 * Fixtures are JSON recorded by tools/capture_demo_fixtures.py from the real
 * FastAPI service, one folder per scenario. Nothing is computed here beyond
 * re-timing timestamps to "now" and adding small jitter to live signals.
 */
import { base } from '$app/paths';
import type {
	Alert,
	Asset,
	DashboardResponse,
	KpiSummary,
	Site,
	TelemetryPoint,
} from '$lib/types';

export const DEMO = import.meta.env.VITE_DEMO_MODE === 'true';

export interface DemoManifest {
	source: 'captured' | 'placeholder';
	captured_at?: string;
	generated_at?: string;
	git_sha?: string;
}

interface ScenarioStatus {
	scenario: string;
	health: string;
	message: string;
}

const DEFAULT_SCENARIO = 'NORMAL';
const TIME_KEYS = new Set([
	'ts',
	'last_seen',
	'opened_at',
	'acked_at',
	'closed_at',
	'due_at',
	'next_deadline_at',
	'last_maint_at',
]);

const STORE_KEY = 'nexus_demo_scenario';

const KNOWN_SCENARIOS = new Set([
	'NORMAL',
	'QUALITY_HOLD_QUENCH',
	'PRESS_BOTTLENECK',
	'STRETCHER_BACKLOG',
	'AGEING_OVEN_DEVIATION',
	'EMERGENCY_PRESS_TRIP',
]);

/** `?scenario=QUALITY_HOLD_QUENCH` deep-links into a fault state. */
function restoreScenario(): string {
	try {
		const fromUrl = new URLSearchParams(location.search).get('scenario')?.toUpperCase();
		if (fromUrl && KNOWN_SCENARIOS.has(fromUrl)) {
			sessionStorage.setItem(STORE_KEY, fromUrl);
			return fromUrl;
		}
		return sessionStorage.getItem(STORE_KEY) || DEFAULT_SCENARIO;
	} catch {
		return DEFAULT_SCENARIO;
	}
}

let current = DEMO ? restoreScenario() : DEFAULT_SCENARIO;
const cache = new Map<string, Promise<unknown>>();
const acked = new Map<string, string>();
const listeners = new Set<(scenario: string) => void>();
let manifestPromise: Promise<DemoManifest> | null = null;

function load<T>(path: string): Promise<T> {
	let p = cache.get(path);
	if (!p) {
		p = fetch(`${base}/demo-fixtures/${path}`).then((r) => {
			if (!r.ok) throw new Error(`demo fixture ${path}: ${r.status}`);
			return r.json();
		});
		cache.set(path, p);
	}
	return p as Promise<T>;
}

export function getManifest(): Promise<DemoManifest> {
	manifestPromise ??= load<DemoManifest>('manifest.json');
	return manifestPromise;
}

async function skewMs(): Promise<number> {
	const m = await getManifest();
	const t = Date.parse(m.captured_at ?? m.generated_at ?? '');
	return Number.isFinite(t) ? Date.now() - t : 0;
}

/** Re-time every known timestamp field by `skew` so fixtures look current. */
function retime<T>(value: T, skew: number): T {
	if (Array.isArray(value)) return value.map((v) => retime(v, skew)) as unknown as T;
	if (value && typeof value === 'object') {
		const out: Record<string, unknown> = {};
		for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
			out[k] =
				TIME_KEYS.has(k) && typeof v === 'string' && Number.isFinite(Date.parse(v))
					? new Date(Date.parse(v) + skew).toISOString()
					: retime(v, skew);
		}
		return out as T;
	}
	return value;
}

async function scenarioData<T>(file: string, scenario = current): Promise<T> {
	const [raw, skew] = await Promise.all([load<T>(`${scenario}/${file}`), skewMs()]);
	return retime(raw, skew);
}

export function currentScenario(): string {
	return current;
}

export function onScenarioChange(fn: (scenario: string) => void): () => void {
	listeners.add(fn);
	return () => listeners.delete(fn);
}

export async function setScenario(name: string): Promise<ScenarioStatus> {
	const upper = name.toUpperCase();
	const status = await load<ScenarioStatus>(`${upper}/scenario.json`); // throws if unknown
	current = upper;
	try {
		sessionStorage.setItem(STORE_KEY, upper);
	} catch {
		/* storage blocked: scenario just resets on reload */
	}
	acked.clear();
	listeners.forEach((fn) => fn(upper));
	return { scenario: status.scenario, health: status.health, message: status.message };
}

export async function getScenario(): Promise<ScenarioStatus> {
	const s = await load<ScenarioStatus>(`${current}/scenario.json`);
	return { scenario: s.scenario, health: s.health, message: s.message };
}

export async function listAssets(): Promise<Asset[]> {
	const [assets, alerts] = await Promise.all([
		scenarioData<Asset[]>('assets.json'),
		listAlerts({ state: 'OPEN' }),
	]);
	const now = new Date().toISOString();
	return assets.map((a) => ({
		...a,
		last_seen: now,
		open_alert_count: alerts.filter((x) => x.asset === a.asset).length,
	}));
}

export async function getAsset(id: string): Promise<Asset> {
	const found = (await listAssets()).find((a) => a.asset === id);
	if (!found) throw new Error(`API 404: asset ${id} not found`);
	return found;
}

export async function getTelemetry(
	id: string,
	opts: { signal?: string; limit?: number } = {},
): Promise<TelemetryPoint[]> {
	const all = await scenarioData<TelemetryPoint[]>(`telemetry/${id}.json`);
	const newest = all.reduce((m, p) => Math.max(m, Date.parse(p.ts)), 0);
	const shift = newest ? Date.now() - newest : 0; // newest point == now
	return all
		.filter((p) => !opts.signal || p.signal === opts.signal)
		.map((p) => ({ ...p, ts: new Date(Date.parse(p.ts) + shift).toISOString() }))
		.sort((a, b) => Date.parse(b.ts) - Date.parse(a.ts))
		.slice(0, opts.limit ?? 500);
}

export async function listAlerts(
	opts: { state?: string; asset?: string; limit?: number } = {},
): Promise<Alert[]> {
	const raw = await scenarioData<Alert[]>('alerts.json');
	const alerts: Alert[] = raw.map((a) =>
		acked.has(a.id) ? { ...a, state: 'ACKED', acked_at: acked.get(a.id)! } : a,
	);
	return alerts
		.filter((a) => !opts.state || a.state === opts.state)
		.filter((a) => !opts.asset || a.asset === opts.asset)
		.slice(0, opts.limit ?? 100);
}

export async function acknowledge(id: string): Promise<{ id: string; state: string }> {
	acked.set(id, new Date().toISOString());
	return { id, state: 'ACKED' };
}

export function listKpis(): Promise<KpiSummary[]> {
	return scenarioData<KpiSummary[]>('kpis.json');
}

export function listSites(): Promise<Site[]> {
	return load<Site[]>('sites.json');
}

export function getDashboard(): Promise<DashboardResponse> {
	return scenarioData<DashboardResponse>('dashboard.json');
}

/** Emulates the SSE endpoints: a frame every 2 s, jittered, re-timed to now. */
export function demoStream<T>(path: string, onMessage: (data: T) => void): () => void {
	const emittedAlerts = new Map<string, Alert>();
	let stopped = false;

	async function tick() {
		try {
			if (path === 'telemetry') {
				for (const a of await listAssets()) {
					const pts = await getTelemetry(a.asset, { limit: 1 });
					const p = pts[0];
					if (!p || stopped) continue;
					const jitter = 1 + (Math.random() - 0.5) * 0.01;
					onMessage({
						...p,
						ts: new Date().toISOString(),
						value: Math.round(p.value * jitter * 100) / 100,
						state: a.state,
					} as T);
				}
			} else if (path === 'alerts') {
				const open = await listAlerts({ limit: 200 });
				const ids = new Set(open.map((a) => a.id));
				// Close alerts from a previous scenario so the badge count falls.
				for (const [id, prev] of emittedAlerts) {
					if (!ids.has(id) && !stopped) {
						onMessage({ ...prev, state: 'CLOSED' } as T);
						emittedAlerts.delete(id);
					}
				}
				for (const a of open) {
					if (stopped) break;
					emittedAlerts.set(a.id, a);
					onMessage(a as T);
				}
			}
		} catch {
			/* fixtures unavailable: stay quiet */
		}
	}

	tick();
	const timer = setInterval(tick, 2000);
	return () => {
		stopped = true;
		clearInterval(timer);
	};
}
