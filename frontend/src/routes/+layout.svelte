<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { api } from '$lib/api';
	import { connectSSE } from '$lib/sse';
	import { assetMap, openAlerts } from '$lib/stores';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import { DEMO, onScenarioChange } from '$lib/demo/replay';
	import type { Alert, Asset, TelemetryPoint } from '$lib/types';

	const nav = [
		{ href: '/dashboard', label: 'Executive View', icon: '🏭' },
		{ href: '/',          label: 'Floor Overview', icon: '⬛' },
		{ href: '/assets',    label: 'Assets',         icon: '🔧' },
		{ href: '/alerts',    label: 'Alerts',         icon: '🔔' },
		{ href: '/kpis',      label: 'KPIs',           icon: '📊' },
		{ href: '/admin',     label: 'Admin',          icon: '⚙️'  },
	];

	let cleanupScenario: (() => void) | null = null;
	let cleanupTelemetry: (() => void) | null = null;
	let cleanupAlerts: (() => void) | null = null;

	async function seedAssets() {
		try {
			const assets = await api.assets.list();
			assetMap.update((m) => {
				assets.forEach((a) => m.set(a.asset, a));
				return new Map(m);
			});
		} catch { /* ignore during dev without backend */ }
	}

	onMount(async () => {
		// Seed asset map from REST on load
		await seedAssets();
		// Demo replay: a scenario switch changes fault codes, not just telemetry
		if (DEMO) cleanupScenario = onScenarioChange(() => void seedAssets());

		// SSE: update asset last_seen + quality from live telemetry
		cleanupTelemetry = connectSSE<TelemetryPoint>('telemetry', (point) => {
			assetMap.update((m) => {
				const existing = m.get(point.asset);
				if (existing) {
					m.set(point.asset, {
						...existing,
						last_seen: point.ts,
						quality: point.quality,
						state: point.state,
					});
				}
				return new Map(m);
			});
		});

		// SSE: refresh open alerts
		cleanupAlerts = connectSSE<Alert>('alerts', (alert) => {
			openAlerts.update((list) => {
				const idx = list.findIndex((a) => a.id === alert.id);
				if (idx >= 0) {
					list[idx] = alert;
				} else {
					list = [alert, ...list];
				}
				return list;
			});
		});
	});

	onDestroy(() => {
		cleanupScenario?.();
		cleanupTelemetry?.();
		cleanupAlerts?.();
	});

	$: path = $page.url.pathname.startsWith(base) ? $page.url.pathname.slice(base.length) || '/' : $page.url.pathname;
	$: openCount = $openAlerts.filter((a) => a.state === 'OPEN').length;
</script>

{#if DEMO}
	<DemoBanner />
{/if}
<div class="layout">
	<aside class="sidebar">
		<div class="logo">
			<span class="logo-mark">⬡</span>
			<span class="logo-text">NEXUS</span>
		</div>
		<nav>
			{#each nav as item}
				<a
					class="nav-item"
					class:active={item.href === '/' ? path === '/' : path.startsWith(item.href)}
					href={`${base}${item.href}`}
				>
					<span class="nav-icon">{item.icon}</span>
					<span class="nav-label">{item.label}</span>
					{#if item.href === '/alerts' && openCount > 0}
						<span class="nav-badge">{openCount}</span>
					{/if}
				</a>
			{/each}
		</nav>
		<div class="sidebar-footer">IIoT Platform v1.0</div>
	</aside>

	<main class="content">
		<slot />
	</main>
</div>

<style>
	:global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
	:global(body) { font-family: 'Inter', system-ui, sans-serif; background: #f9fafb; color: #111827; }
	:global(a) { color: inherit; }

	.layout {
		display: flex;
		min-height: 100vh;
	}

	.sidebar {
		width: 220px;
		min-height: 100vh;
		background: #1e1b4b;
		color: #c7d2fe;
		display: flex;
		flex-direction: column;
		padding: 0;
		flex-shrink: 0;
	}

	.logo {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 20px 20px 24px;
		border-bottom: 1px solid #312e81;
	}
	.logo-mark { font-size: 1.6rem; color: #818cf8; }
	.logo-text  { font-size: 1.1rem; font-weight: 800; color: #fff; letter-spacing: 0.1em; }

	nav { display: flex; flex-direction: column; padding: 12px 0; flex: 1; }

	.nav-item {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 20px;
		text-decoration: none;
		color: #c7d2fe;
		font-size: 0.875rem;
		border-left: 3px solid transparent;
		transition: background 0.1s, color 0.1s;
	}
	.nav-item:hover { background: #312e81; color: #fff; }
	.nav-item.active { background: #312e81; color: #fff; border-left-color: #818cf8; }
	.nav-icon { font-size: 1rem; width: 20px; text-align: center; }
	.nav-badge {
		margin-left: auto;
		background: #ef4444;
		color: #fff;
		border-radius: 999px;
		font-size: 0.65rem;
		font-weight: 700;
		padding: 1px 7px;
	}

	.sidebar-footer {
		padding: 16px 20px;
		font-size: 0.7rem;
		color: #4c1d95;
		border-top: 1px solid #312e81;
	}

	.content {
		flex: 1;
		padding: 28px 32px;
		overflow-y: auto;
	}
</style>
