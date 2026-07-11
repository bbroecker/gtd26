/* ============================================================
   German Throwdown 2026 — Leaderboard App
   Reads data/data-{slug}.json, renders Overall + Per-WOD tables.
   ============================================================ */

'use strict';

const COMPETITIONS = {
  gtd: { name: 'German Throwdown 2026', url: 'https://germanthrowdown.de' },
  atd: { name: 'Austrian Throwdown 2026', url: 'https://austrianthrowdown.at' },
};

let appData = null;
let currentDivision = null;
let activeTab = 'overall';
let currentWod = null;
let currentView = 'division'; // 'division' | 'all_individual' | 'all_teams'
let currentCompSlug = 'gtd';

// ---------------------------------------------------------------------------
// Initialise
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  await loadCompetition('gtd');
  bindEvents();
});

async function loadCompetition(slug) {
  currentCompSlug = slug;
  const comp = COMPETITIONS[slug];
  if (comp) {
    document.getElementById('pageTitle').textContent = comp.name;
    const link = document.querySelector('.gtd-link');
    if (link) link.href = comp.url;
  }
  await loadData(slug);
}

async function loadData(slug) {
  try {
    const res = await fetch(`data/data-${slug}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    appData = await res.json();
    populateDivisionSelect();
    setLastUpdated();
    // Default to combined individual view, fall back to preferred division
    const divSelect = document.getElementById('divisionSelect');
    divSelect.value = 'all_individual';
    if (!divSelect.value) {
      const preferred = ['Intermediate Male', 'Elite Male', 'Intermediate Female', 'Elite Female'];
      for (const name of preferred) {
        const opt = [...divSelect.options].find(o => o.text === name);
        if (opt) { divSelect.value = opt.value; break; }
      }
    }
    if (divSelect.value) onDivisionChange();
  } catch (e) {
    console.error(`Failed to load data/data-${slug}.json:`, e);
    document.getElementById('overallContainer').innerHTML =
      `<p class="empty-state">⚠️ Could not load data.<br>
       Run <code>python3 fetch.py</code> to generate <code>data/data-${slug}.json</code>, then reload.</p>`;
  }
}

function setLastUpdated() {
  if (!appData?.meta?.updated_at_readable) return;
  document.getElementById('lastUpdated').textContent =
    `Last updated: ${appData.meta.updated_at_readable}`;
}

function populateDivisionSelect() {
  const sel = document.getElementById('divisionSelect');
  sel.innerHTML = '';
  const divisions = appData?.divisions || [];
  const hasIndividuals = divisions.some(d => d.individual);
  const hasTeams = divisions.some(d => !d.individual);

  // Combined view options at the top
  if (hasIndividuals) {
    const opt = document.createElement('option');
    opt.value = 'all_individual';
    opt.textContent = 'All Athletes (Combined)';
    sel.appendChild(opt);
  }
  if (hasTeams) {
    const opt = document.createElement('option');
    opt.value = 'all_teams';
    opt.textContent = 'All Teams (Combined)';
    sel.appendChild(opt);
  }
  if (divisions.length) {
    const sep = document.createElement('option');
    sep.disabled = true;
    sep.textContent = '──────────────';
    sel.appendChild(sep);
  }

  // Individual divisions
  const indivDivs = divisions.filter(d => d.individual);
  if (indivDivs.length) {
    const group = document.createElement('optgroup');
    group.label = 'Individual';
    indivDivs.forEach(div => {
      const opt = document.createElement('option');
      opt.value = divisions.indexOf(div);
      opt.textContent = div.name;
      group.appendChild(opt);
    });
    sel.appendChild(group);
  }

  // Team divisions
  const teamDivs = divisions.filter(d => !d.individual);
  if (teamDivs.length) {
    const group = document.createElement('optgroup');
    group.label = 'Teams';
    teamDivs.forEach(div => {
      const opt = document.createElement('option');
      opt.value = divisions.indexOf(div);
      opt.textContent = div.name;
      group.appendChild(opt);
    });
    sel.appendChild(group);
  }
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------
function bindEvents() {
  document.getElementById('competitionSelect').addEventListener('change', async (e) => {
    await loadCompetition(e.target.value);
  });
  document.getElementById('divisionSelect').addEventListener('change', onDivisionChange);
  document.getElementById('wodSelect').addEventListener('change', onWodChange);

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      activeTab = btn.dataset.tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b === btn));
      document.querySelectorAll('.tab-content').forEach(c =>
        c.classList.toggle('active', c.id === `tab-${activeTab}`)
      );
      if (activeTab === 'perwod' && currentDivision) renderPerWod();
    });
  });
}

function onDivisionChange() {
  const idx = document.getElementById('divisionSelect').value;
  if (idx === '') return;

  // Combined cross-division views
  if (idx === 'all_individual' || idx === 'all_teams') {
    currentView = idx;
    currentDivision = null;
    currentWod = null;
    const teamMode = idx === 'all_teams';
    const relevant = appData.divisions.filter(d => teamMode ? !d.individual : d.individual);
    const totalResults = relevant.reduce((s, d) => s + (d.result_count || 0), 0);
    document.getElementById('divisionStats').textContent =
      `${totalResults} ${teamMode ? 'teams' : 'athletes'} with results · ${relevant.length} divisions`;
    document.getElementById('tabs').style.display = 'none';
    document.getElementById('wodControls').style.display = 'none';
    document.getElementById('tab-perwod').classList.remove('active');
    document.getElementById('tab-overall').classList.add('active');
    activeTab = 'overall';
    document.querySelectorAll('.tab-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.tab === 'overall'));
    renderCombined(teamMode);
    return;
  }

  currentView = 'division';
  currentDivision = appData.divisions[idx];
  currentWod = null;

  // Stats
  const stats = document.getElementById('divisionStats');
  const unit = currentDivision.individual ? 'athlete' : 'team';
  stats.textContent =
    `${currentDivision.result_count} ${unit}s with results · ` +
    `${currentDivision.athlete_count} registered · ` +
    `${currentDivision.wods.length} workout${currentDivision.wods.length !== 1 ? 's' : ''}`;

  // Show tabs
  document.getElementById('tabs').style.display = '';

  // Populate WOD select
  const wodSel = document.getElementById('wodSelect');
  wodSel.innerHTML = '';
  currentDivision.wods.forEach(wname => {
    const opt = document.createElement('option');
    opt.value = wname;
    opt.textContent = wname;
    wodSel.appendChild(opt);
  });
  currentWod = currentDivision.wods[0] || null;
  document.getElementById('wodControls').style.display = currentDivision.wods.length ? '' : 'none';

  if (activeTab === 'overall') renderOverall();
  else renderPerWod();
}

function onWodChange() {
  currentWod = document.getElementById('wodSelect').value;
  renderPerWod();
}

// ---------------------------------------------------------------------------
// Overall table
// ---------------------------------------------------------------------------
function renderOverall() {
  const container = document.getElementById('overallContainer');
  const div = currentDivision;
  if (!div || !div.overall?.length) {
    container.innerHTML = '<p class="no-results">No results yet for this division.</p>';
    return;
  }

  const wods = div.wods;

  let html = '<div class="table-wrapper"><table>';

  // Header
  html += '<thead><tr>';
  html += '<th class="num">#</th>';
  html += '<th>Athlete</th>';
  wods.forEach(w => { html += `<th class="num">${escHtml(w)}</th>`; });
  html += '<th class="num">Points</th>';
  html += '</tr></thead>';

  // Body
  html += '<tbody>';
  div.overall.forEach(athlete => {
    const rankClass = athlete.rank <= 3 ? `rank-${athlete.rank}` : 'rank-other';
    html += `<tr class="${rankClass}">`;

    // Rank
    html += `<td class="num"><span class="rank-badge">${athlete.rank}</span></td>`;

    // Name + club
    const flag = countryFlag(athlete.country);
    html += `<td>
      <div class="athlete-name">${flag}${escHtml(athlete.name)}</div>
      ${athlete.club ? `<div class="athlete-club">${escHtml(athlete.club)}</div>` : ''}
    </td>`;

    // Per-WOD cells: position + score
    wods.forEach(wname => {
      const wod = athlete.wods?.[wname];
      if (!wod) {
        html += `<td class="wod-pos none">—</td>`;
        return;
      }
      const posClass = wod.position === 1 ? 'p1' : wod.position === 2 ? 'p2' :
                       wod.position === 3 ? 'p3' : wod.position <= 10 ? 'top10' : '';
      const scoreStr = formatScore(wod.time, wod.reps, wod.tiebreak, wod.cap, div.wod_units?.[wname]);
      const membersHtml = renderMemberScores(wod.members, wod.cap, div.wod_units?.[wname]);
      html += `<td class="wod-pos ${posClass}">
        <div>#${wod.position}</div>
        ${scoreStr ? `<div style="font-size:0.75rem;opacity:0.75;font-weight:normal">${scoreStr}</div>` : ''}
        ${membersHtml}
      </td>`;
    });

    // Points
    html += `<td class="points-cell">${athlete.points}</td>`;
    html += '</tr>';
  });

  html += '</tbody></table></div>';
  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Combined (all-divisions) table
// ---------------------------------------------------------------------------
function renderCombined(teamMode) {
  const container = document.getElementById('overallContainer');
  const relevant = appData.divisions.filter(d => teamMode ? !d.individual : d.individual);

  const allAthletes = [];
  for (const div of relevant) {
    for (const athlete of (div.overall || [])) {
      allAthletes.push({ ...athlete, division: div.name });
    }
  }

  if (!allAthletes.length) {
    container.innerHTML = '<p class="no-results">No results yet across any division.</p>';
    return;
  }

  // Collect unique WOD names in order (preserve first-seen order across divisions)
  // and build a unit map across all relevant divisions
  const wodSet = new Set();
  const wodUnits = {};
  relevant.forEach(div => {
    (div.wods || []).forEach(w => wodSet.add(w));
    Object.assign(wodUnits, div.wod_units || {});
  });
  const wods = [...wodSet];

  // Sort by points ascending (lower = better in CrossFit), break ties alphabetically
  allAthletes.sort((a, b) => (a.points || 0) - (b.points || 0) || a.name.localeCompare(b.name));
  allAthletes.forEach((a, i) => { a.rank = i + 1; });

  const colLabel = teamMode ? 'Team' : 'Athlete';
  let html = '<div class="table-wrapper"><table>';
  html += '<thead><tr>';
  html += '<th class="num">#</th>';
  html += `<th>${colLabel}</th>`;
  html += '<th>Division</th>';
  wods.forEach(w => { html += `<th class="num">${escHtml(w)}</th>`; });
  html += '<th class="num">Points</th>';
  html += '</tr></thead>';

  html += '<tbody>';
  allAthletes.forEach(athlete => {
    const rankClass = athlete.rank <= 3 ? `rank-${athlete.rank}` : 'rank-other';
    const flag = countryFlag(athlete.country);
    html += `<tr class="${rankClass}">`;
    html += `<td class="num"><span class="rank-badge">${athlete.rank}</span></td>`;
    html += `<td>
      <div class="athlete-name">${flag}${escHtml(athlete.name)}</div>
      ${athlete.club ? `<div class="athlete-club">${escHtml(athlete.club)}</div>` : ''}
    </td>`;
    html += `<td class="division-cell">${escHtml(athlete.division)}</td>`;
    wods.forEach(wname => {
      const wod = athlete.wods?.[wname];
      if (!wod) {
        html += `<td class="wod-pos none">—</td>`;
        return;
      }
      const posClass = wod.position === 1 ? 'p1' : wod.position === 2 ? 'p2' :
                       wod.position === 3 ? 'p3' : wod.position <= 10 ? 'top10' : '';
      const scoreStr = formatScore(wod.time, wod.reps, wod.tiebreak, wod.cap, wodUnits[wname]);
      const membersHtml = renderMemberScores(wod.members, wod.cap, wodUnits[wname]);
      html += `<td class="wod-pos ${posClass}">
        <div>#${wod.position}</div>
        ${scoreStr ? `<div style="font-size:0.75rem;opacity:0.75;font-weight:normal">${scoreStr}</div>` : ''}
        ${membersHtml}
      </td>`;
    });
    html += `<td class="points-cell">${athlete.points}</td>`;
    html += '</tr>';
  });

  html += '</tbody></table></div>';
  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Per-WOD table
// ---------------------------------------------------------------------------
function renderPerWod() {
  const container = document.getElementById('wodContainer');
  const div = currentDivision;
  if (!div || !currentWod) {
    container.innerHTML = '<p class="no-results">Select a workout above.</p>';
    return;
  }

  // Sync WOD select
  document.getElementById('wodSelect').value = currentWod;

  const rows = div.per_wod?.[currentWod];
  if (!rows?.length) {
    container.innerHTML = `<p class="no-results">No results for ${escHtml(currentWod)} yet.</p>`;
    return;
  }

  let html = '<div class="table-wrapper"><table>';
  html += '<thead><tr>';
  html += '<th class="num">#</th>';
  html += '<th>Athlete</th>';
  html += '<th class="num">Score</th>';
  html += '</tr></thead>';

  html += '<tbody>';
  rows.forEach(r => {
    const rankClass = r.rank <= 3 ? `rank-${r.rank}` : 'rank-other';
    const flag = countryFlag(r.country);
    const scoreStr = formatScore(r.time, r.reps, r.tiebreak, r.cap, div.wod_units?.[currentWod]) || '—';
    const membersHtml = renderMemberScores(r.members, r.cap, div.wod_units?.[currentWod]);
    html += `<tr class="${rankClass}">
      <td class="num"><span class="rank-badge">${r.rank}</span></td>
      <td>
        <div class="athlete-name">${flag}${escHtml(r.name)}</div>
        ${r.club ? `<div class="athlete-club">${escHtml(r.club)}</div>` : ''}
        ${membersHtml}
      </td>
      <td class="score-cell num">${scoreStr}</td>
    </tr>`;
  });

  html += '</tbody></table></div>';
  container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Score formatting
// ---------------------------------------------------------------------------
function formatScore(time, reps, tiebreak, cap, unit) {
  // Determine display label from API unit string
  const unitLabel = unit && unit.toLowerCase().startsWith('kilo') ? 'kg' : 'reps';
  // Capped: explicit cap flag OR both time and reps present (API cap flag is unreliable)
  const isCapped = cap || (time != null && time > 0 && reps != null && reps > 0);
  if (isCapped && reps != null && reps > 0) {
    const base = `${reps} ${unitLabel}`;
    if (tiebreak != null && tiebreak > 0) {
      return `${base} @ ${fmtTime(tiebreak)}`;
    }
    return base;
  }
  // Finished under cap — show time
  if (time != null && time > 0) {
    return fmtTime(time);
  }
  // AMRAP / max weight — only reps, no time
  if (reps != null && reps > 0) {
    const base = `${reps} ${unitLabel}`;
    if (tiebreak != null && tiebreak > 0) {
      return `${base} @ ${fmtTime(tiebreak)}`;
    }
    return base;
  }
  return '';
}

function fmtTime(ms) {
  if (ms == null) return '';
  const totalSec = Math.round(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}:${pad(m)}:${pad(s)}`;
  return `${m}:${pad(s)}`;
}

function pad(n) { return String(n).padStart(2, '0'); }

// ---------------------------------------------------------------------------
// Member scores sub-display (teams only)
// ---------------------------------------------------------------------------
function renderMemberScores(members, teamCap, unit) {
  if (!members || !members.length) return '';
  const genderIcon = g => g === 'm' ? '♂' : g === 'f' ? '♀' : '';
  const lines = members.map(m => {
    const score = formatScore(m.time, m.reps, m.tiebreak, m.cap, unit);
    const capBadge = m.cap ? ' ⏱' : '';
    return `<div class="member-score">${genderIcon(m.gender)} ${escHtml(m.name)}: ${score || '—'}${capBadge}</div>`;
  });
  return `<div class="member-scores">${lines.join('')}</div>`;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function escHtml(str) {
  return String(str ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Simple country code → flag emoji
function countryFlag(code) {
  if (!code || code.length !== 2) return '';
  try {
    const flag = code.toUpperCase().replace(/./g, c =>
      String.fromCodePoint(c.charCodeAt(0) + 0x1F1A5));
    return `<span class="flag">${flag}</span>`;
  } catch {
    return '';
  }
}
