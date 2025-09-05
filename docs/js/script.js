// script.js
(function () {
    const DATA_URL = 'data/data.json'; // served from docs/
    const PRODUCTS = [
        { id: 'firefox', label: 'Firefox Desktop' },
        { id: 'fenix', label: 'Firefox for Android' },
    ];

    const $ = sel => document.querySelector(sel);
    const localeSelect = $('#localeSelect');
    const statusEl = $('#status');
    const chartEl = $('#chart');
    let chart;

    const urlParams = new URLSearchParams(location.search);

    function setURLParam(key, value) {
        const params = new URLSearchParams(location.search);
        if (value) params.set(key, value); else params.delete(key);
        history.replaceState(null, '', `${location.pathname}?${params.toString()}`);
    }

    function normalizeLocale(loc) {
        return (loc || '').toLowerCase().replace('_', '-');
    }

    function parseAcceptLanguage() {
        const langs = (navigator.languages && navigator.languages.length
            ? navigator.languages
            : [navigator.language || 'en']).map(normalizeLocale);
        const expanded = new Set();
        langs.forEach(l => {
            expanded.add(l);
            const base = l.split('-')[0];
            if (base) expanded.add(base);
        });
        return Array.from(expanded);
    }

    // Versions are integers in your JSON → simple numeric sort
    function versionCompare(a, b) {
        return Number(a) - Number(b);
    }

    function pickDefaultLocale(allLocales) {
        const param = normalizeLocale(urlParams.get('locale'));
        if (param && allLocales.has(param)) return param;
        const accept = parseAcceptLanguage();
        for (const loc of accept) {
            if (allLocales.has(loc)) return loc;
            const base = loc.split('-')[0];
            if (allLocales.has(base)) return base;
        }
        return allLocales.values().next().value;
    }

    function setStatus(msg, isError = false) {
        statusEl.textContent = msg;
        statusEl.className = isError ? 'error' : 'loading';
    }

    async function init() {
        try {
            setStatus('Loading data…');
            const res = await fetch(DATA_URL);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const db = await res.json();

            // Build locale list from JSON top-level keys
            const allLocales = new Set(Object.keys(db).map(normalizeLocale));
            if (!allLocales.size) throw new Error('No locales found in data.json');

            const localesSorted = Array.from(allLocales).sort((a, b) => a.localeCompare(b));
            localeSelect.innerHTML = localesSorted.map(l => `<option value="${l}">${l}</option>`).join('');

            const chosen = pickDefaultLocale(allLocales);
            localeSelect.value = chosen;
            if (urlParams.get('locale') !== chosen) setURLParam('locale', chosen);

            await render(db, chosen);

            localeSelect.addEventListener('change', async () => {
                const locale = localeSelect.value;
                setURLParam('locale', locale);
                await render(db, locale);
            });
        } catch (err) {
            console.error(err);
            setStatus(`Failed to load data: ${err.message}`, true);
        }
    }

    function collectLabelsForLocale(db, locale) {
        // Expected JSON shape: db[locale][product][version] = value (0..1)
        const entry = db[locale];
        if (!entry) return [];
        const versions = new Set();
        for (const p of PRODUCTS) {
            const prodObj = entry[p.id] || {};
            Object.keys(prodObj).forEach(v => versions.add(v));
        }
        return Array.from(versions).sort(versionCompare);
    }

    async function render(db, locale) {
        const entry = db[locale];
        if (!entry) {
            setStatus(`No data found for locale "${locale}".`, true);
            if (chart) { chart.destroy(); chart = null; }
            return;
        }

        const labels = collectLabelsForLocale(db, locale);
        if (!labels.length) {
            setStatus(`No versions found for locale "${locale}".`, true);
            if (chart) { chart.destroy(); chart = null; }
            return;
        }

        const datasets = PRODUCTS.map(p => {
            const prodObj = entry[p.id] || {};
            // Map each version label to a percentage value; use null when missing (Span gaps)
            const values = labels.map(v => (v in prodObj ? prodObj[v] * 100 : null));
            return {
                label: p.label,
                data: values,
                spanGaps: true,
                tension: 0.25,
                borderWidth: 2.5,
                pointRadius: 3,
                pointHoverRadius: 5,
            };
        });

        const data = { labels, datasets };
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 350 },
            plugins: {
                legend: { display: true, labels: { color: '#303541ff' } },
                tooltip: {
                    callbacks: {
                        label: (ctx) =>
                            `${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) : '—'}%`,
                    },
                },
            },
            scales: {
                x: { ticks: { color: '#232428ff' }, grid: { color: 'rgba(104, 93, 93, 0.17)' } },
                y: {
                    min: 0,
                    max: 100,
                    title: { display: true, text: 'Completion %', color: '#232428ff' },
                    ticks: { color: '#232428ff', callback: v => v + '%' },
                    grid: { color: 'rgba(255,255,255,0.06)' },
                },
            },
        };

        if (chart) chart.destroy();
        chart = new Chart(chartEl, { type: 'line', data, options });
        setStatus(`Showing ${labels.length} versions for ${locale}.`);
    }

    init();
})();
