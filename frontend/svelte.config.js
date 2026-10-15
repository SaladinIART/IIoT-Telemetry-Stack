import adapter from '@sveltejs/adapter-static';

// Demo build (npm run build:demo): browser-only replay hosted under a sub-path
// on GitHub Pages. Normal build writes into the API image's static dir.
const demo = process.env.VITE_DEMO_MODE === 'true';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({
			pages: demo ? 'build-demo' : '../services/api/static',
			assets: demo ? 'build-demo' : '../services/api/static',
			fallback: demo ? '404.html' : 'index.html',
			precompress: false,
			strict: false,
		}),
		paths: {
			base: process.env.BASE_PATH ?? '',
		},
	},
};

export default config;
