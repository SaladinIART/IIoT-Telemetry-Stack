<script lang="ts">
	import { base } from '$app/paths';
	import type { Asset } from '$lib/types';
	import AlertBadge from './AlertBadge.svelte';
	import StatusPill from './StatusPill.svelte';

	export let asset: Asset;
</script>

<a class="card" href="{base}/assets/{asset.asset}">
	<div class="card-header">
		<span class="asset-name">{asset.display_name}</span>
		<AlertBadge count={asset.open_alert_count} severity="warning" />
	</div>
	<div class="asset-type">{asset.asset_type} · {asset.line_name}</div>
	<div class="card-status">
		<StatusPill state={asset.state} quality={asset.quality} />
		{#if asset.fault_code > 0}
			<span class="fault-code">F{asset.fault_code}</span>
		{/if}
	</div>
	<div class="last-seen">
		{asset.last_seen
			? new Date(asset.last_seen).toLocaleTimeString()
			: 'No data'}
	</div>
</a>

<style>
	.card {
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 16px;
		border: 1px solid #e5e7eb;
		border-radius: 10px;
		background: #fff;
		text-decoration: none;
		color: inherit;
		transition: box-shadow 0.15s, border-color 0.15s;
	}
	.card:hover {
		box-shadow: 0 4px 12px rgba(0,0,0,0.08);
		border-color: #6366f1;
	}
	.card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.asset-name {
		font-weight: 600;
		font-size: 1rem;
		color: #111827;
	}
	.asset-type {
		font-size: 0.75rem;
		color: #6b7280;
	}
	.card-status {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.fault-code {
		font-size: 0.72rem;
		color: #dc2626;
		font-weight: 600;
	}
	.last-seen {
		font-size: 0.7rem;
		color: #9ca3af;
	}
</style>
