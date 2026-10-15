<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api';
	import { DEMO } from '$lib/demo/replay';
	import type { Site } from '$lib/types';

	let apiKey = '';
	let sites: Site[] = [];
	let loading = true;
	let saved = false;

	onMount(async () => {
		apiKey = localStorage.getItem('nexus_api_key') ?? 'nexus-dev-key-change-me';
		try {
			sites = await api.sites.list();
		} catch { /* ignore */ }
		loading = false;
	});

	function saveKey() {
		localStorage.setItem('nexus_api_key', apiKey);
		saved = true;
		setTimeout(() => (saved = false), 2000);
	}
</script>

<h1>Admin</h1>
<p class="subtitle">Platform configuration and diagnostics</p>

<section class="card">
	<h2>API Key</h2>
	<p class="help">The API key is stored in your browser's localStorage and sent as the <code>X-API-Key</code> header on every request.</p>
	<div class="key-row">
		<input type="text" bind:value={apiKey} class="key-input" autocomplete="off" />
		<button class="save-btn" on:click={saveKey}>{saved ? '✓ Saved' : 'Save'}</button>
	</div>
</section>

<section class="card">
	<h2>Sites</h2>
	{#if loading}
		<p class="loading">Loading…</p>
	{:else if sites.length === 0}
		<p class="empty">No sites found.</p>
	{:else}
		<table>
			<thead><tr><th>ID</th><th>Display Name</th><th>Location</th><th>Timezone</th><th>Active</th></tr></thead>
			<tbody>
				{#each sites as s (s.site_id)}
					<tr>
						<td><code>{s.site_id}</code></td>
						<td>{s.display_name}</td>
						<td>{s.location}</td>
						<td>{s.timezone}</td>
						<td>{s.active ? '✓' : '✗'}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>

<section class="card">
	<h2>Quick Links</h2>
	<ul class="links">
		{#if !DEMO}
		<li><a href="/docs" target="_blank" rel="noreferrer">API Documentation (Swagger UI)</a></li>
		<li><a href="/redoc" target="_blank" rel="noreferrer">API Documentation (ReDoc)</a></li>
		<li><a href="http://localhost:3000" target="_blank" rel="noreferrer">Grafana Operator Dashboards</a></li>
		{/if}
	</ul>
</section>

<style>
	h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }
	.subtitle { font-size: 0.82rem; color: #6b7280; margin-bottom: 24px; }
	.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
	h2 { font-size: 1rem; font-weight: 600; margin-bottom: 10px; }
	.help { font-size: 0.82rem; color: #6b7280; margin-bottom: 10px; }
	code { font-family: monospace; background: #f3f4f6; padding: 1px 5px; border-radius: 4px; font-size: 0.85em; }
	.key-row { display: flex; gap: 8px; }
	.key-input { flex: 1; font-size: 0.85rem; padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-family: monospace; }
	.save-btn { padding: 6px 16px; background: #4f46e5; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; font-weight: 600; }
	.save-btn:hover { background: #4338ca; }
	table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
	th { text-align: left; padding: 6px 8px; border-bottom: 1px solid #e5e7eb; color: #6b7280; font-weight: 600; }
	td { padding: 6px 8px; border-bottom: 1px solid #f3f4f6; }
	.links { list-style: none; display: flex; flex-direction: column; gap: 8px; }
	.links a { color: #4f46e5; font-size: 0.85rem; text-decoration: none; }
	.links a:hover { text-decoration: underline; }
	.loading, .empty { color: #6b7280; font-size: 0.9rem; }
</style>
