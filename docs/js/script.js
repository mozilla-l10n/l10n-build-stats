const PRODUCTS = [
    { id: 'firefox', label: 'Firefox Desktop', color: '#ff6b35', darkColor: '#ff8566' },
    { id: 'fenix', label: 'Firefox for Android', color: '#4ecdc4', darkColor: '#6ee7de' },
];

// Color palette for comparison mode
const COMPARISON_COLORS = [
    { light: '#ff6b35', dark: '#ff8566' },
    { light: '#4ecdc4', dark: '#6ee7de' },
    { light: '#9b59b6', dark: '#b389d4' },
    { light: '#2ecc71', dark: '#5fe399' },
    { light: '#f39c12', dark: '#f5b759' },
    { light: '#e74c3c', dark: '#ec7063' },
    { light: '#3498db', dark: '#5dade2' },
    { light: '#1abc9c', dark: '#48c9b0' },
];

// DOM elements
const localeSearch = document.querySelector('#localeSearch');
const localeSelect = document.querySelector('#localeSelect');
const localeCount = document.querySelector('#localeCount');
const statusEl = document.querySelector('#status');
const chartEl = document.querySelector('#chart');
const themeToggle = document.querySelector('#themeToggle');
const exportBtn = document.querySelector('#exportBtn');
const compareMode = document.querySelector('#compareMode');
const clearSelectionBtn = document.querySelector('#clearSelectionBtn');
const selectedLocalesDiv = document.querySelector('#selectedLocales');
const statsCard = document.querySelector('#statsCard');
const skeleton = document.querySelector('#skeleton');
const lastUpdated = document.querySelector('#lastUpdated');

let chart;
let allLocales = [];
let db = null;
let isCompareMode = false;
let selectedLocales = [];

const urlParams = new URLSearchParams(location.search);

// Theme management
function initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    setTheme(theme);
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    themeToggle.querySelector('.theme-icon').textContent = theme === 'dark' ? '☀️' : '🌙';

    // Update chart colors if chart exists
    if (chart && db) {
        const locale = localeSelect.value;
        render(db, locale, db[locale]?.name);
    }
}

themeToggle.addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    setTheme(current === 'dark' ? 'light' : 'dark');
});

// URL management
function setURLParam(key, value) {
    const params = new URLSearchParams(location.search);
    if (value) params.set(key, value); else params.delete(key);
    history.replaceState(null, '', `${location.pathname}?${params.toString()}`);
}

function parseAcceptLanguage() {
    const langs = (navigator.languages && navigator.languages.length
        ? navigator.languages
        : [navigator.language || 'en']);
    const expanded = new Set();
    langs.forEach(l => {
        expanded.add(l);
        const base = l.split('-')[0];
        if (base) expanded.add(base);
    });
    return Array.from(expanded);
}

function versionCompare(a, b) {
    const pa = a.split('.').map(Number);
    const pb = b.split('.').map(Number);
    const len = Math.max(pa.length, pb.length);
    for (let i = 0; i < len; i++) {
        const va = pa[i] ?? 0;
        const vb = pb[i] ?? 0;
        if (va !== vb) return va - vb;
    }
    return 0;
}

// Map of version string → x-axis position, populated from the loaded data
// so dot releases space evenly between their bounding major versions
// regardless of which dot release numbers actually shipped.
let versionPositions = new Map();

function isDotRelease(v) {
    const parts = v.split('.').map(Number);
    return parts.length > 2 && (parts[2] || 0) > 0;
}

// Build a global version → x map from the dataset. Major releases land on
// integers ("150.0" → 150). Dot releases for a given major are sorted and
// spaced evenly in the open interval (major, major+1), so e.g. dot releases
// .2, .3, .4, .5 for 151 land at 151.2, 151.4, 151.6, 151.8.
function buildVersionPositions(db) {
    const allVersions = new Set();
    for (const locale of Object.keys(db)) {
        const entry = db[locale];
        for (const p of PRODUCTS) {
            Object.keys(entry[p.id] || {}).forEach(v => allVersions.add(v));
        }
    }

    const dotsByMajor = new Map();
    const positions = new Map();
    for (const v of allVersions) {
        const major = Number(v.split('.')[0]) || 0;
        if (isDotRelease(v)) {
            if (!dotsByMajor.has(major)) dotsByMajor.set(major, []);
            dotsByMajor.get(major).push(v);
        } else {
            positions.set(v, major);
        }
    }

    for (const [major, versions] of dotsByMajor) {
        versions.sort(versionCompare);
        const step = 1 / (versions.length + 1);
        versions.forEach((v, i) => positions.set(v, major + (i + 1) * step));
    }

    return positions;
}

function versionToX(v) {
    if (versionPositions.has(v)) return versionPositions.get(v);
    // Fallback for versions not in the precomputed map.
    const parts = v.split('.').map(Number);
    const major = parts[0] || 0;
    const dot = parts[2] || 0;
    return major + dot * 0.25;
}

// Linear-scale tick callback: only render labels at integer positions
// (i.e. major releases). Dot-release positions get an empty label and just
// appear as data markers on the chart.
function majorVersionTickCallback(value) {
    return Number.isInteger(value) ? value + '.0' : '';
}

function isDotReleasePoint(ctx) {
    const v = ctx?.raw?.version;
    return typeof v === 'string' && v.split('.').length > 2;
}

function buildChartOptions({ isDark, xMin, xMax, legend }) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 350 },
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: isDark ? '#f9fafb' : '#303541ff',
                    ...legend,
                },
            },
            tooltip: {
                callbacks: {
                    title: (items) => items[0]?.raw?.version || '',
                    label: (ctx) =>
                        `${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(2) : '—'}%`,
                },
            },
            zoom: {
                zoom: {
                    wheel: { enabled: true },
                    pinch: { enabled: true },
                    mode: 'x',
                },
                pan: {
                    enabled: true,
                    mode: 'x',
                },
                limits: {
                    x: { min: 'original', max: 'original' },
                },
            },
        },
        scales: {
            x: {
                type: 'linear',
                min: xMin,
                max: xMax,
                ticks: {
                    color: isDark ? '#9ca3af' : '#374151',
                    stepSize: 1,
                    autoSkip: false,
                    maxRotation: 0,
                    callback: majorVersionTickCallback,
                },
                grid: { color: isDark ? 'rgba(75, 85, 99, 0.3)' : 'rgba(104, 93, 93, 0.17)' },
            },
            y: {
                grace: '5%',
                title: {
                    display: true,
                    text: 'Completion %',
                    color: isDark ? '#9ca3af' : '#374151',
                    font: { size: 13 },
                },
                ticks: {
                    color: isDark ? '#9ca3af' : '#374151',
                    callback: v => (v > 100 ? '' : v.toFixed(2) + '%'),
                },
                grid: { color: isDark ? 'rgba(75, 85, 99, 0.3)' : 'rgba(229, 231, 235, 0.5)' },
            },
        },
        interaction: {
            intersect: false,
            mode: 'index',
        },
    };
}

function xRangeFromLabels(labels) {
    if (!labels.length) return { xMin: undefined, xMax: undefined };
    const xs = labels.map(versionToX);
    return { xMin: Math.floor(Math.min(...xs)), xMax: Math.ceil(Math.max(...xs)) };
}

function pickDefaultLocale(allLocales) {
    const param = urlParams.get('locale');
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

function showSkeleton(show) {
    skeleton.classList.toggle('show', show);
}

// Locale search functionality
function filterLocales(searchTerm) {
    const term = searchTerm.toLowerCase();
    const options = Array.from(localeSelect.options);

    options.forEach(option => {
        const text = option.textContent.toLowerCase();
        const matches = text.includes(term);
        option.style.display = matches ? '' : 'none';
    });

    // Select first visible option
    const firstVisible = options.find(opt => opt.style.display !== 'none');
    if (firstVisible && searchTerm) {
        localeSelect.value = firstVisible.value;
    }
}

localeSearch.addEventListener('input', (e) => {
    filterLocales(e.target.value);
});

localeSearch.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        const firstVisible = Array.from(localeSelect.options)
            .find(opt => opt.style.display !== 'none');
        if (firstVisible) {
            localeSelect.value = firstVisible.value;
            localeSelect.dispatchEvent(new Event('change'));
            localeSearch.value = '';
            filterLocales('');
        }
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        localeSelect.focus();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Focus search on '/'
    if (e.key === '/' && !['INPUT', 'SELECT'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        localeSearch.focus();
    }
});

// Comparison mode toggle
compareMode.addEventListener('change', (e) => {
    isCompareMode = e.target.checked;

    if (isCompareMode) {
        // Enable multi-select
        localeSelect.removeAttribute('size');
        clearSelectionBtn.style.display = '';
        selectedLocalesDiv.style.display = 'flex';

        // Get currently selected locale(s)
        const selected = Array.from(localeSelect.selectedOptions).map(opt => opt.value);
        if (selected.length === 0 && localeSelect.value) {
            selectedLocales = [localeSelect.value];
        } else {
            selectedLocales = selected;
        }

        updateSelectedLocalesTags();
        renderComparison();
    } else {
        // Disable multi-select
        localeSelect.setAttribute('size', '8');
        clearSelectionBtn.style.display = 'none';
        selectedLocalesDiv.style.display = 'none';

        // Keep only first selected locale
        const firstLocale = selectedLocales[0] || localeSelect.value;
        selectedLocales = [];
        localeSelect.value = firstLocale;

        render(db, firstLocale, db[firstLocale]?.name);
    }
});

// Handle locale selection in compare mode
localeSelect.addEventListener('change', () => {
    if (isCompareMode) {
        selectedLocales = Array.from(localeSelect.selectedOptions).map(opt => opt.value);
        updateSelectedLocalesTags();
        renderComparison();
    } else {
        const locale = localeSelect.value;
        setURLParam('locale', locale);
        render(db, locale, db[locale]?.name);
    }
});

// Clear selection button
clearSelectionBtn.addEventListener('click', () => {
    selectedLocales = [];
    Array.from(localeSelect.options).forEach(opt => opt.selected = false);
    updateSelectedLocalesTags();
    if (chart) {
        chart.destroy();
        chart = null;
    }
    setStatus('Select locales to compare');
    statsCard.style.display = 'none';
});

// Update selected locales tags
function updateSelectedLocalesTags() {
    if (!isCompareMode || selectedLocales.length === 0) {
        selectedLocalesDiv.innerHTML = '';
        return;
    }

    selectedLocalesDiv.innerHTML = selectedLocales.map(locale => {
        const name = db[locale]?.name || '';
        return `
            <div class="locale-tag">
                ${locale}${name ? ' – ' + name : ''}
                <span class="remove" data-locale="${locale}">×</span>
            </div>
        `;
    }).join('');

    // Add click handlers for remove buttons
    selectedLocalesDiv.querySelectorAll('.remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const locale = e.target.getAttribute('data-locale');
            selectedLocales = selectedLocales.filter(l => l !== locale);

            // Update select element
            Array.from(localeSelect.options).forEach(opt => {
                if (opt.value === locale) opt.selected = false;
            });

            updateSelectedLocalesTags();
            if (selectedLocales.length > 0) {
                renderComparison();
            } else {
                if (chart) chart.destroy();
                chart = null;
                setStatus('Select locales to compare');
                statsCard.style.display = 'none';
            }
        });
    });
}

// Export chart as image
exportBtn.addEventListener('click', () => {
    if (!chart) return;
    const url = chartEl.toDataURL('image/png');
    const link = document.createElement('a');
    const filename = isCompareMode
        ? `l10n-stats-comparison-${selectedLocales.join('-')}.png`
        : `l10n-stats-${localeSelect.value}.png`;
    link.download = filename;
    link.href = url;
    link.click();
});

// Compute avg + latest per product. `dataByProduct` is { [productId]: [{x,y,version}, ...] }.
function calculateProductStats(dataByProduct) {
    const out = {};
    for (const p of PRODUCTS) {
        const points = (dataByProduct[p.id] || []).filter(pt => pt && pt.y != null);
        if (!points.length) { out[p.id] = null; continue; }
        const ys = points.map(pt => pt.y);
        const avg = ys.reduce((a, b) => a + b, 0) / ys.length;
        const latest = points.reduce((best, pt) => (pt.x > best.x ? pt : best), points[0]).y;
        out[p.id] = { avg, latest };
    }
    return out;
}

function renderStatRows(containerId, stats, key) {
    const html = PRODUCTS.map(p => {
        const s = stats[p.id];
        const value = s ? s[key].toFixed(2) + '%' : '—';
        const complete = s && s[key] === 100 ? ' complete' : '';
        return `
            <div class="stat-row">
                <span class="stat-product">${p.label}</span>
                <span class="stat-product-value${complete}">${value}</span>
            </div>`;
    }).join('');
    document.getElementById(containerId).innerHTML = html;
}

function updateStatsPanel(datasets) {
    if (!datasets.length) {
        statsCard.style.display = 'none';
        return;
    }

    const byProduct = {};
    datasets.forEach(ds => {
        const pid = ds.productId;
        if (!pid) return;
        (byProduct[pid] ||= []).push(...ds.data);
    });

    const stats = calculateProductStats(byProduct);
    if (!PRODUCTS.some(p => stats[p.id])) {
        statsCard.style.display = 'none';
        return;
    }

    renderStatRows('statAvgRows', stats, 'avg');
    renderStatRows('statLatestRows', stats, 'latest');
    statsCard.style.display = 'block';
}

async function init() {
    try {
        initTheme();
        showSkeleton(true);
        setStatus('Loading data…');

        const res = await fetch('data/data.json', { cache: 'no-cache' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        db = await res.json();

        versionPositions = buildVersionPositions(db);

        // Build locale list from JSON top-level keys
        const allLocalesSet = new Set(Object.keys(db));
        if (!allLocalesSet.size) throw new Error('No locales found in data.json');

        allLocales = Array.from(allLocalesSet).sort((a, b) => a.localeCompare(b));
        localeSelect.innerHTML = allLocales
            .map(l => {
                const entry = db[l];
                const name = entry?.name || '';
                return `<option value="${l}">${l}${name ? ' – ' + name : ''}</option>`;
            })
            .join('');

        localeCount.textContent = `(${allLocales.length} locales)`;

        const chosen = pickDefaultLocale(allLocalesSet);
        localeSelect.value = chosen;
        if (urlParams.get('locale') !== chosen) setURLParam('locale', chosen);

        // Get last modified from response headers
        const lastMod = res.headers.get('last-modified');
        if (lastMod) {
            const date = new Date(lastMod);
            lastUpdated.textContent = ` • Last updated: ${date.toLocaleDateString()}`;
        }

        await render(db, chosen, db[chosen]?.name);
        showSkeleton(false);
    } catch (err) {
        console.error(err);
        showSkeleton(false);
        setStatus(`Failed to load data: ${err.message}`, true);
    }
}

function collectLabelsForLocale(db, locale) {
    const entry = db[locale];
    if (!entry) return [];
    const versions = new Set();
    for (const p of PRODUCTS) {
        const prodObj = entry[p.id] || {};
        Object.keys(prodObj).forEach(v => versions.add(v));
    }
    return Array.from(versions).sort(versionCompare);
}

async function render(db, locale, locale_name) {
    const entry = db[locale];
    if (!entry) {
        setStatus(`No data found for locale "${locale}".`, true);
        if (chart) { chart.destroy(); chart = null; }
        statsCard.style.display = 'none';
        return;
    }

    const labels = collectLabelsForLocale(db, locale);
    if (!labels.length) {
        setStatus(`No versions found for locale "${locale}".`, true);
        if (chart) { chart.destroy(); chart = null; }
        statsCard.style.display = 'none';
        return;
    }

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

    const datasets = PRODUCTS.map(p => {
        const prodObj = entry[p.id] || {};
        const data = labels.map(v => ({
            x: versionToX(v),
            y: v in prodObj ? prodObj[v] * 100 : null,
            version: v,
        }));
        return {
            label: p.label,
            productId: p.id,
            data,
            borderColor: isDark ? p.darkColor : p.color,
            backgroundColor: isDark ? p.darkColor + '20' : p.color + '20',
            spanGaps: true,
            tension: 0.25,
            borderWidth: 2.5,
            pointRadius: ctx => isDotReleasePoint(ctx) ? 1.5 : 3,
            pointHoverRadius: ctx => isDotReleasePoint(ctx) ? 3 : 5,
            pointBackgroundColor: isDark ? p.darkColor : p.color,
        };
    });

    const { xMin, xMax } = xRangeFromLabels(labels);
    const options = buildChartOptions({
        isDark,
        xMin,
        xMax,
        legend: { font: { size: 13 }, padding: 15 },
    });

    if (chart) chart.destroy();
    chart = new Chart(chartEl, { type: 'line', data: { datasets }, options });

    updateStatsPanel(datasets);
    setStatus(`Showing ${labels.length} versions for ${locale_name || locale} (${locale}). Use mouse wheel to zoom, drag to pan.`);
}

// Render comparison mode with multiple locales
function renderComparison() {
    if (!selectedLocales.length) {
        setStatus('Select locales to compare');
        if (chart) chart.destroy();
        chart = null;
        statsCard.style.display = 'none';
        return;
    }

    // Collect all versions from all selected locales
    const allVersions = new Set();
    selectedLocales.forEach(locale => {
        const labels = collectLabelsForLocale(db, locale);
        labels.forEach(v => allVersions.add(v));
    });

    const labels = Array.from(allVersions).sort(versionCompare);
    if (!labels.length) {
        setStatus('No version data found for selected locales', true);
        if (chart) chart.destroy();
        chart = null;
        statsCard.style.display = 'none';
        return;
    }

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const datasets = [];

    // Create datasets for each locale
    selectedLocales.forEach((locale, localeIdx) => {
        const entry = db[locale];
        if (!entry) return;

        const localeName = entry.name || locale;
        const colorPalette = COMPARISON_COLORS[localeIdx % COMPARISON_COLORS.length];

        PRODUCTS.forEach((product, prodIdx) => {
            const prodObj = entry[product.id] || {};
            const data = labels.map(v => ({
                x: versionToX(v),
                y: v in prodObj ? prodObj[v] * 100 : null,
                version: v,
            }));

            // Use different line styles for products within the same locale
            const dashPattern = prodIdx === 0 ? [] : [5, 5];

            datasets.push({
                label: `${localeName} – ${product.label}`,
                data,
                borderColor: isDark ? colorPalette.dark : colorPalette.light,
                backgroundColor: (isDark ? colorPalette.dark : colorPalette.light) + '20',
                borderDash: dashPattern,
                spanGaps: true,
                tension: 0.25,
                borderWidth: 2.5,
                pointRadius: ctx => isDotReleasePoint(ctx) ? 1 : 2,
                pointHoverRadius: ctx => isDotReleasePoint(ctx) ? 2.5 : 4,
                pointBackgroundColor: isDark ? colorPalette.dark : colorPalette.light,
            });
        });
    });

    const { xMin, xMax } = xRangeFromLabels(labels);
    const options = buildChartOptions({
        isDark,
        xMin,
        xMax,
        legend: { font: { size: 12 }, padding: 10, boxWidth: 30 },
    });

    if (chart) chart.destroy();
    chart = new Chart(chartEl, { type: 'line', data: { datasets }, options });

    statsCard.style.display = 'none';
    setStatus(`Comparing ${selectedLocales.length} locale${selectedLocales.length > 1 ? 's' : ''} across ${labels.length} versions. Use mouse wheel to zoom, drag to pan.`);
}

init();
