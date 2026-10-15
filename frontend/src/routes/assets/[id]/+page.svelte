<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { base } from '$app/paths';
	import { api } from '$lib/api';
	import SignalChart from '$lib/components/SignalChart.svelte';
	import StatusPill from '$lib/components/StatusPill.svelte';
	import type { Alert, Asset, TelemetryPoint } from '$lib/types';

	let asset: Asset | null = null;
	let signals: string[] = [];
	let selectedSignal = '';
	let points: TelemetryPoint[] = [];
	let alerts: Alert[] = [];
	let loading = true;
	let error = '';

	$: assetId = $page.params.id;

	onMount(async () => {
		if (!assetId) {
			error = 'Missing asset id.';
			loading = false;
			return;
		}

		try {
			asset = await api.assets.get(assetId);
			// Fetch distinct signals by loading a small sample
			const sample = await api.assets.telemetry(assetId, { limit: 200 });
			signals = [...new Set(sample.map((p) => p.signal))].sort();
			selectedSignal = signals[0] ?? '';
			alerts = await api.alerts.list({ asset: assetId, limit: 20 });
			if (selectedSignal) await loadSignal();
		} catch (e) {
			error = String(e);
		} finally {
			loading = false;
		}
	});

	async function loadSignal() {
		if (!assetId || !selectedSignal) {
			points = [];
			return;
		}

		points = await api.assets.telemetry(assetId, { signal: selectedSignal, limit: 300 });
		// Chart expects ascending time order
		points = [...points].reverse();
	}
</script>

<a class="back" href="{base}/assets">← Assets</a>

{#if loading}
	<p class="loading">Loading…</p>
{:else if error}
	<p class="error">{error}</p>
{:else if asset}
	<div class="header">
		<div>
			<h1>{asset.display_name}</h1>
			<p class="meta">{asset.asset_type} · {asset.line_name} · {asset.site}</p>
		</div>
		<StatusPill state={asset.state} quality={asset.quality} />
	</div>

	<div class="stats">
		<div class="stat"><div class="stat-label">Fault Code</div><div class="stat-value">{asset.fault_code}</div></div>
		<div class="stat"><div class="stat-label">Quality</div><div class="stat-value">{asset.quality}</div></div>
		<div class="stat"><div class="stat-label">Open Alerts</div><div class="stat-value alert-count">{asset.open_alert_count}</div></div>
		<div class="stat"><div class="stat-label">Last Seen</div><div class="stat-value">{asset.last_seen ? new Date(asset.last_seen).toLocaleString() : '—'}</div></div>
	</div>

	<!-- Signal chart -->
	<section class="card">
		<div class="card-header">
			<h2>Signal History</h2>
			<select bind:value={selectedSignal} on:change={loadSignal}>
				{#each signals as s}
					<option value={s}>{s}</option>
				{/each}
			</select>
		</div>
		{#if points.length > 0}
			<SignalChart {points} signal={selectedSignal} />
		{:else}
			<p class="empty">No telemetry data yet.</p>
		{/if}
	</section>

	<!-- Recent alerts for this asset -->
	<section class="card">
		<h2>Recent Alerts</h2>
		{#if alerts.length === 0}
			<p class="empty">No alerts recorded.</p>
		{:else}
			<table>
				<thead><tr><th>Time</th><th>Signal</th><th>Type</th><th>Severity</th><th>Message</th><th>State</th></tr></thead>
				<tbody>
					{#each alerts as al (al.id)}
						<tr>
							<td>{new Date(al.opened_at).toLocaleString()}</td>
							<td>{al.signal}</td>
							<td>{al.alert_type}</td>
							<td class="sev sev-{al.severity}">{al.severity}</td>
							<td>{al.message}</td>
							<td>{al.state}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
{/if}

<style>
	.back { font-size: 0.85rem; color: #6366f1; text-decoration: none; display: inline-block; margin-bottom: 16px; }
	.back:hover { text-decoration: underline; }
	h1 { font-size: 1.5rem; font-weight: 700; }
	.meta { font-size: 0.8rem; color: #6b7280; margin-top: 2px; }
	.header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 20px; }
	.stats { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
	.stat { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; min-width: 110px; }
	.stat-label { font-size: 0.72rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
	.stat-value { font-size: 1.1rem; font-weight: 600; margin-top: 2px; }
	.alert-count { color: #dc2626; }
	.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
	.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
	h2 { font-size: 1rem; font-weight: 600; }
	select { font-size: 0.85rem; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 6px; }
	table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
	th { text-align: left; padding: 6px 8px; border-bottom: 1px solid #e5e7eb; color: #6b7280; font-weight: 600; }
	td { padding: 6px 8px; border-bottom: 1px solid #f3f4f6; }
	.sev-critical { color: #dc2626; font-weight: 600; }
	.sev-warning  { color: #d97706; font-weight: 600; }
	.sev-info     { color: #2563eb; }
	.loading, .empty { color: #6b7280; font-size: 0.9rem; }
	.error { color: #dc2626; }
</style>
