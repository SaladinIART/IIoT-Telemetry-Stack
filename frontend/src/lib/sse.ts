import { DEMO, demoStream } from './demo/replay';

/**
 * Creates a managed SSE connection that automatically reconnects on failure.
 * Returns a cleanup function — call it to close the connection.
 */
export function connectSSE<T>(
	path: string,
	onMessage: (data: T) => void,
	onError?: (err: Event) => void,
): () => void {
	if (DEMO) return demoStream<T>(path, onMessage);

	const apiKey =
		(typeof localStorage !== 'undefined' && localStorage.getItem('nexus_api_key')) ||
		'nexus-dev-key-change-me';

	const url = `/api/v1/stream/${path}?api_key=${encodeURIComponent(apiKey)}`;
	let es: EventSource | null = null;
	let closed = false;
	let retryTimer: ReturnType<typeof setTimeout> | null = null;

	function connect() {
		if (closed) return;
		es = new EventSource(url);

		es.onmessage = (ev) => {
			try {
				onMessage(JSON.parse(ev.data) as T);
			} catch {
				// ignore malformed frames
			}
		};

		es.onerror = (err) => {
			onError?.(err);
			es?.close();
			es = null;
			if (!closed) {
				retryTimer = setTimeout(connect, 3000);
			}
		};
	}

	connect();

	return () => {
		closed = true;
		if (retryTimer) clearTimeout(retryTimer);
		es?.close();
	};
}
