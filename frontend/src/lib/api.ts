import * as demo from './demo/replay';
import type { Alert, Asset, DashboardResponse, KpiSummary, Site, TelemetryPoint } from './types';

const BASE = '/api/v1';

function apiKey(): string {
	return (typeof localStorage !== 'undefined' && localStorage.getItem('nexus_api_key')) ||
		'nexus-dev-key-change-me';
}

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
	const url = new URL(BASE + path, window.location.origin);
	if (params) {
		Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
	}
	const resp = await fetch(url.toString(), {
		headers: { 'X-API-Key': apiKey() },
	});
	if (!resp.ok) throw new Error(`API ${resp.status}: ${await resp.text()}`);
	return resp.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
	const resp = await fetch(BASE + path, {
		method: 'POST',
		headers: { 'X-API-Key': apiKey(), 'Content-Type': 'application/json' },
		body: JSON.stringify(body),
	});
	if (!resp.ok) throw new Error(`API ${resp.status}: ${await resp.text()}`);
	return resp.json() as Promise<T>;
}

const live = {
	assets: {
		list: () => get<Asset[]>('/assets'),
		get: (id: string) => get<Asset>(`/assets/${id}`),
		telemetry: (
			id: string,
			opts: { signal?: string; from?: string; to?: string; limit?: number } = {},
		) => get<TelemetryPoint[]>(`/assets/${id}/telemetry`, opts as Record<string, string | number>),
	},
	alerts: {
		list: (opts: { state?: string; asset?: string; limit?: number } = {}) =>
			get<Alert[]>('/alerts', opts as Record<string, string | number>),
		acknowledge: (id: string) => post<{ id: string; state: string }>(`/alerts/${id}/acknowledge`, {}),
	},
	kpis: {
		list: (window = 8) => get<KpiSummary[]>('/kpis', { window }),
	},
	sites: {
		list: () => get<Site[]>('/sites'),
	},
	dashboard: {
		get: () => get<DashboardResponse>('/dashboard'),
	},
	demo: {
		setScenario: (name: string) =>
			post<{ scenario: string; health: string; message: string }>(`/demo/scenario/${name}`, {}),
		getScenario: () => get<{ scenario: string; health: string; message: string }>('/demo/scenario'),
	},
};

/** Browser-replay implementation of the same surface (VITE_DEMO_MODE=true). */
const replay: typeof live = {
	assets: {
		list: () => demo.listAssets(),
		get: (id) => demo.getAsset(id),
		telemetry: (id, opts = {}) => demo.getTelemetry(id, opts),
	},
	alerts: {
		list: (opts = {}) => demo.listAlerts(opts),
		acknowledge: (id) => demo.acknowledge(id),
	},
	kpis: { list: () => demo.listKpis() },
	sites: { list: () => demo.listSites() },
	dashboard: { get: () => demo.getDashboard() },
	demo: {
		setScenario: (name) => demo.setScenario(name),
		getScenario: () => demo.getScenario(),
	},
};

export const api: typeof live = demo.DEMO ? replay : live;
