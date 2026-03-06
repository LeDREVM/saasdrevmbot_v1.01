/**
 * Export Markdown vers le dossier sync Nextcloud de saasDrevmbot
 * Reproduit le format de markdown_exporter.py pour compatibilité Obsidian.
 *
 * Dossier cible : NEXTCLOUD_REPORTS_DIR (défaut: Nextcloud/saasDrevmbot/GoldyXbOT/reports/)
 */

const fs   = require('fs');
const path = require('path');

const REPORTS_DIR = process.env.NEXTCLOUD_REPORTS_DIR
  || path.join(process.env.USERPROFILE || process.env.HOME || '', 'Nextcloud', 'saasDrevmbot', 'GoldyXbOT', 'reports');

// S'assurer que le dossier existe
function ensureDir(dir) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`[Nextcloud] Dossier créé: ${dir}`);
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10);
}

function nowFr() {
  return new Date().toLocaleString('fr-FR', { timeZone: process.env.TIMEZONE || 'Europe/Paris' });
}

function impactLabel(lvl) {
  return { 3: 'Fort 🔴', 2: 'Moyen 🟠', 1: 'Faible 🟡', 0: 'Aucun ⚪' }[lvl] ?? 'N/A';
}

// ─── Export résumé journalier ─────────────────────────────────────────────────

/**
 * Exporte le résumé du jour en .md dans le dossier Nextcloud.
 * Format compatible avec Obsidian (front matter YAML).
 *
 * @param {Object[]} events  - événements filtrés du jour
 * @returns {string}          - chemin du fichier créé
 */
function exportDailyCalendar(events) {
  ensureDir(REPORTS_DIR);

  const date     = today();
  const filename = `calendar_${date}.md`;
  const filepath = path.join(REPORTS_DIR, filename);

  const high   = events.filter(e => e.impactLevel >= 3);
  const medium = events.filter(e => e.impactLevel === 2);
  const low    = events.filter(e => e.impactLevel === 1);

  // Grouper par source
  const bySource = {};
  events.forEach(e => {
    bySource[e.source] = (bySource[e.source] || 0) + 1;
  });

  const sourcesStr = Object.entries(bySource).map(([s, n]) => `${s} (${n})`).join(', ');

  let md = `---
title: Calendrier Économique ${date}
date: ${date}
tags: [trading, calendar, economic-events, goldyxbot]
source: GoldyXbOT
generated: "${nowFr()}"
---

# 📅 CALENDRIER ÉCONOMIQUE — ${date}

**Généré par:** GoldyXbOT
**Sources:** ${sourcesStr || 'N/A'}
**Total annonces:** **${events.length}**
**Généré le:** ${nowFr()}

---

## 📊 RÉSUMÉ

| Impact | Nombre |
|--------|--------|
| 🔴 Fort | **${high.length}** |
| 🟠 Moyen | **${medium.length}** |
| 🟡 Faible | **${low.length}** |

`;

  // ── Section Fort impact ──────────────────────────────
  if (high.length > 0) {
    md += `---\n\n## 🔴 IMPACT FORT\n\n`;
    md += `| Heure | Devise | Événement | Prévision | Précédent | Résultat |\n`;
    md += `|-------|--------|-----------|-----------|-----------|----------|\n`;
    high.forEach(e => {
      md += `| ${e.time || '—'} | **${e.currency}** | ${e.event} | ${e.forecast || '—'} | ${e.previous || '—'} | ${e.actual || '_en attente_'} |\n`;
    });
    md += '\n';
  }

  // ── Section Moyen impact ─────────────────────────────
  if (medium.length > 0) {
    md += `---\n\n## 🟠 IMPACT MOYEN\n\n`;
    md += `| Heure | Devise | Événement | Prévision | Précédent | Résultat |\n`;
    md += `|-------|--------|-----------|-----------|-----------|----------|\n`;
    medium.forEach(e => {
      md += `| ${e.time || '—'} | **${e.currency}** | ${e.event} | ${e.forecast || '—'} | ${e.previous || '—'} | ${e.actual || '_en attente_'} |\n`;
    });
    md += '\n';
  }

  // ── Section Faible impact ────────────────────────────
  if (low.length > 0) {
    md += `---\n\n## 🟡 IMPACT FAIBLE\n\n`;
    md += `| Heure | Devise | Événement | Prévision | Précédent |\n`;
    md += `|-------|--------|-----------|-----------|----------|\n`;
    low.slice(0, 20).forEach(e => { // Max 20 pour éviter les rapports géants
      md += `| ${e.time || '—'} | **${e.currency}** | ${e.event} | ${e.forecast || '—'} | ${e.previous || '—'} |\n`;
    });
    if (low.length > 20) md += `\n_...et ${low.length - 20} autres événements faibles_\n`;
    md += '\n';
  }

  if (events.length === 0) {
    md += `\n> Aucune annonce trouvée pour ce jour.\n\n`;
  }

  // ── Devises actives ──────────────────────────────────
  const currencyCounts = {};
  events.forEach(e => {
    currencyCounts[e.currency] = (currencyCounts[e.currency] || 0) + 1;
  });
  const sortedCurrencies = Object.entries(currencyCounts).sort((a, b) => b[1] - a[1]);

  if (sortedCurrencies.length > 0) {
    md += `---\n\n## 💱 DEVISES ACTIVES\n\n`;
    sortedCurrencies.forEach(([cur, cnt]) => {
      md += `- **${cur}**: ${cnt} annonce(s)\n`;
    });
    md += '\n';
  }

  // ── Footer ───────────────────────────────────────────
  md += `---

## 🔗 LIENS UTILES

- [ForexFactory Calendar](https://www.forexfactory.com/calendar)
- [Investing.com Economic Calendar](https://www.investing.com/economic-calendar/)

---

## 🔄 SYNCHRONISATION

Ce rapport est généré automatiquement par **GoldyXbOT** et synchronisé via **Nextcloud**.

| Info | Valeur |
|------|--------|
| Dossier | \`GoldyXbOT/reports/\` |
| Dashboard | http://localhost:${process.env.PORT || 3000} |
| Prochain scan | Toutes les ${process.env.CHECK_INTERVAL || 5} minutes |

---

_Ces données sont issues du scraping automatique et ne constituent pas un conseil financier._
`;

  fs.writeFileSync(filepath, md, 'utf-8');
  console.log(`[Nextcloud] ✅ Rapport exporté: ${filename}`);
  return filepath;
}

// ─── Export résumé avec résultats (post-annonce) ──────────────────────────────

/**
 * Met à jour le rapport du jour avec les résultats (actual).
 * Appelé quand des résultats sont publiés en cours de journée.
 *
 * @param {Object[]} events - événements avec actual mis à jour
 * @returns {string|null}
 */
function updateDailyResults(events) {
  const eventsWithResults = events.filter(e => e.actual);
  if (eventsWithResults.length === 0) return null;

  ensureDir(REPORTS_DIR);

  const date     = today();
  const filename = `results_${date}.md`;
  const filepath = path.join(REPORTS_DIR, filename);

  let md = `---
title: Résultats Économiques ${date}
date: ${date}
tags: [trading, results, economic-events, goldyxbot]
source: GoldyXbOT
generated: "${nowFr()}"
---

# ✅ RÉSULTATS ÉCONOMIQUES — ${date}

**Mis à jour:** ${nowFr()}
**Annonces avec résultat:** **${eventsWithResults.length}**

---

## 📊 RÉSULTATS PUBLIÉS

| Heure | Devise | Événement | Prévision | Précédent | ✅ Résultat |
|-------|--------|-----------|-----------|-----------|------------|
`;

  eventsWithResults
    .sort((a, b) => (a.time || '').localeCompare(b.time || ''))
    .forEach(e => {
      // Évaluer si résultat beat/miss
      const forecast = parseFloat(e.forecast);
      const actual   = parseFloat(e.actual);
      let indicator  = '';
      if (!isNaN(forecast) && !isNaN(actual)) {
        indicator = actual > forecast ? ' ⬆️' : actual < forecast ? ' ⬇️' : ' ↔️';
      }
      md += `| ${e.time || '—'} | **${e.currency}** | ${e.event} | ${e.forecast || '—'} | ${e.previous || '—'} | **${e.actual}**${indicator} |\n`;
    });

  md += `
---

_Rapport mis à jour automatiquement par GoldyXbOT_
`;

  fs.writeFileSync(filepath, md, 'utf-8');
  console.log(`[Nextcloud] ✅ Résultats exportés: ${filename} (${eventsWithResults.length} résultats)`);
  return filepath;
}

// ─── Export index hebdomadaire ────────────────────────────────────────────────

/**
 * Génère/met à jour l'INDEX.md du dossier reports pour navigation Obsidian.
 */
function updateIndex() {
  ensureDir(REPORTS_DIR);

  const indexPath = path.join(REPORTS_DIR, 'INDEX.md');

  // Lister tous les fichiers .md du dossier
  const files = fs.readdirSync(REPORTS_DIR)
    .filter(f => f.endsWith('.md') && f !== 'INDEX.md')
    .sort()
    .reverse(); // Plus récent en premier

  const calendarFiles = files.filter(f => f.startsWith('calendar_'));
  const resultFiles   = files.filter(f => f.startsWith('results_'));

  let md = `---
title: Index GoldyXbOT Reports
tags: [goldyxbot, index]
---

# 📁 GoldyXbOT — Index des Rapports

**Dashboard:** http://localhost:${process.env.PORT || 3000}
**Mis à jour:** ${nowFr()}

---

## 📅 Calendriers Quotidiens

`;

  calendarFiles.slice(0, 30).forEach(f => {
    const date = f.replace('calendar_', '').replace('.md', '');
    md += `- [[${f.replace('.md', '')}|📅 ${date}]]\n`;
  });

  md += `\n---\n\n## ✅ Résultats\n\n`;

  resultFiles.slice(0, 30).forEach(f => {
    const date = f.replace('results_', '').replace('.md', '');
    md += `- [[${f.replace('.md', '')}|✅ ${date}]]\n`;
  });

  md += `\n---\n_Index généré automatiquement par GoldyXbOT_\n`;

  fs.writeFileSync(indexPath, md, 'utf-8');
}

module.exports = {
  exportDailyCalendar,
  updateDailyResults,
  updateIndex,
  REPORTS_DIR,
};
