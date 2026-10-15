<script lang="ts">
	import { onMount } from 'svelte';
	import { getManifest } from '$lib/demo/replay';

	const REPO = 'https://github.com/SaladinIART/IIoT-Telemetry-Stack';

	let source: 'captured' | 'placeholder' | 'unknown' = 'unknown';
	let when = '';

	onMount(async () => {
		try {
			const m = await getManifest();
			source = m.source;
			const t = m.captured_at ?? m.generated_at;
			when = t ? new Date(t).toLocaleDateString() : '';
		} catch {
			/* banner still shows the core message */
		}
	});
</script>

<div class="banner" role="note">
	<strong>Browser replay.</strong>
	{#if source === 'captured'}
		Every value was recorded from the real NEXUS pipeline{when ? ` on ${when}` : ''}; the equipment is simulated.
	{:else}
		<span class="warn">Sample data: not yet captured from the live pipeline.</span> Equipment is simulated.
	{/if}
	<a href={REPO} target="_blank" rel="noreferrer">Run the full stack with Docker →</a>
</div>

<style>
	.banner {
		background: #1e1b4b;
		color: #e0e7ff;
		font-size: 0.8rem;
		padding: 0.5rem 1rem;
		line-height: 1.4;
	}
	.warn {
		color: #fcd34d;
		font-weight: 600;
	}
	a {
		color: #a5b4fc;
		margin-left: 0.5rem;
		white-space: nowrap;
	}
</style>
