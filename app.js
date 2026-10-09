document.addEventListener('DOMContentLoaded', () => {
    fetch(`data.json?v=${new Date().getTime()}`)
        .then(response => {
            if (!response.ok) throw new Error('Data file not found.');
            return response.json();
        })
        .then(data => {
            // Index Page Logic
            if (document.getElementById('league-name')) {
                if (data.league && data.league.name) {
                    document.getElementById('league-name').innerText = data.league.name;
                }
                if (data.last_updated) {
                    const updateDate = new Date(data.last_updated);
                    const timeString = updateDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    document.getElementById('last-updated-text').innerText = `Updated: ${timeString}`;
                }

                const standings = data.standings ? data.standings.results : [];
                if (data.top_prem_players && data.top_prem_players.length > 0) {
                    renderTopPlayers(data.top_prem_players);
                }
                renderPodium(standings.slice(0, 3));
                renderTable(standings);
                renderChart(standings);
            }

            // Fixtures Page Logic
            if (document.getElementById('fixtures-container')) {
                renderFixtures(data.fixtures, data.gameweek);
            }

            // Manager Summary Page Logic
            if (document.getElementById('manager-select')) {
                initManagerDropdown(data.manager_summaries);
                
                // Read URL query parameter ?id=ENTRY_ID
                const urlParams = new URLSearchParams(window.location.search);
                const entryId = urlParams.get('id');
                if (entryId && data.manager_summaries[entryId]) {
                    document.getElementById('manager-select').value = entryId;
                    loadManagerProfile(entryId, data.manager_summaries);
                }
            }
        })
        .catch(error => {
            console.error('Error loading data:', error);
        });
});

function renderTable(standings) {
    const tbody = document.getElementById('league-table-body');
    if (!tbody) return;
    let tableHTML = '';

    const highestGW = Math.max(...standings.map(m => m.event_total || 0));
    const firstPlacePts = standings[0] ? standings[0].total : 0;

    standings.forEach((manager, index) => {
        let form = '-';
        if (manager.gw_history && manager.gw_history.length > 0) {
            const last3 = manager.gw_history.slice(-3);
            const sum = last3.reduce((a, b) => a + b, 0);
            form = (sum / last3.length).toFixed(1);
        }

        const prevPts = index > 0 ? standings[index - 1].total : manager.total;
        const gapVal = index === 0 ? 0 : (prevPts - manager.total);
        const toFirstVal = index === 0 ? 0 : (firstPlacePts - manager.total);

        const gapStr = gapVal === 0 ? '-' : `-${gapVal}`;
        const toFirstStr = toFirstVal === 0 ? '-' : `-${toFirstVal}`;

        let arrow = '<span class="arrow-flat">—</span>';
        if (manager.rank < manager.last_rank) arrow = '<span class="arrow-up">▲</span>';
        else if (manager.rank > manager.last_rank) arrow = '<span class="arrow-down">▼</span>';

        const motwBadge = (manager.event_total === highestGW && highestGW > 0) 
            ? '<span class="motw-badge">🔥 MOTW</span>' 
            : '';

        tableHTML += `
            <tr>
                <td>
                    <div class="rank-movement">
                        <span>${manager.rank}</span>
                        ${arrow}
                    </div>
                </td>
                <td>
                    <div class="team-info">
                        <a href="manager.html?id=${manager.entry}" class="team-name" style="text-decoration:none;">${manager.entry_name} ${motwBadge}</a>
                        <span class="manager-name">${manager.player_name}</span>
                    </div>
                </td>
                <td class="center-col"><span class="pts-gw" style="color:var(--text-main); font-weight:700;">${form}</span></td>
                <td class="center-col"><span class="pts-gw">${manager.event_total}</span></td>
                <td class="center-col"><span class="pts-total">${manager.total}</span></td>
                <td class="center-col"><span class="diff-badge">${gapStr}</span></td>
                <td class="center-col"><span class="diff-badge diff-1st">${toFirstStr}</span></td>
            </tr>
        `;
    });
    tbody.innerHTML = tableHTML;
}

function renderFixtures(fixtures, gw) {
    const container = document.getElementById('fixtures-container');
    const title = document.getElementById('fixture-gw-title');
    if (!container) return;

    if (title && gw) title.innerText = `Gameweek ${gw} Fixtures`;

    let html = '';
    fixtures.forEach(f => {
        const score = f.finished ? `${f.home_score} - ${f.away_score}` : 'vs';
        html += `
            <div class="fixture-card">
                <div class="fixture-team home">${f.home_team} (${f.home_team_code})</div>
                <div class="fixture-score">${score}</div>
                <div class="fixture-team away">${f.away_team} (${f.away_team_code})</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function initManagerDropdown(summaries) {
    const select = document.getElementById('manager-select');
    if (!select || !summaries) return;

    Object.values(summaries).forEach(m => {
        const opt = document.createElement('option');
        opt.value = m.entry_id;
        opt.textContent = `${m.entry_name} (${m.player_name})`;
        select.appendChild(opt);
    });

    window.allSummaries = summaries; // Store reference globally for quick lookup
}

function loadManagerProfile(entryId, summariesData) {
    const summaries = summariesData || window.allSummaries;
    if (!summaries || !summaries[entryId]) return;

    const mgr = summaries[entryId];
    document.getElementById('manager-details-container').style.display = 'block';

    document.getElementById('mgr-name').innerText = mgr.entry_name;
    document.getElementById('mgr-team').innerText = `Manager: ${mgr.player_name}`;
    document.getElementById('mgr-rank').innerText = `#${mgr.overall_rank}`;
    document.getElementById('mgr-total').innerText = mgr.total_points;
    document.getElementById('mgr-gw').innerText = mgr.gw_points;

    // Chips
    const chipsDiv = document.getElementById('mgr-chips');
    if (mgr.chips_used && mgr.chips_used.length > 0) {
        chipsDiv.innerHTML = mgr.chips_used.map(c => `<span class="diff-badge">${c.name.toUpperCase()} (GW${c.event})</span>`).join('');
    } else {
        chipsDiv.innerHTML = '<em>No chips played yet this season.</em>';
    }

    // Past History
    const pastTbody = document.getElementById('mgr-past-history');
    if (mgr.past_seasons && mgr.past_seasons.length > 0) {
        pastTbody.innerHTML = mgr.past_seasons.map(s => `
            <tr>
                <td>${s.season_name}</td>
                <td>${s.total_points}</td>
                <td>#${s.rank.toLocaleString()}</td>
            </tr>
        `).join('');
    } else {
        pastTbody.innerHTML = '<tr><td colspan="3">No previous season history available.</td></tr>';
    }
}

function renderTopPlayers(players) {
    const container = document.getElementById('top-players-container');
    if (!container) return;
    container.style.display = 'grid';
    let html = '';
    
    players.forEach(p => {
        html += `
            <div class="player-card">
                <div class="player-info">
                    <span class="player-pos">${p.position}</span>
                    <span class="player-name">${p.name}</span>
                    <span class="player-team">${p.team}</span>
                </div>
                <div class="player-pts">${p.points}</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderPodium(topManagers) {
    const podiumContainer = document.getElementById('podium-container');
    if (!podiumContainer || topManagers.length === 0) return;
    podiumContainer.style.display = 'grid';

    let podiumHTML = '';
    topManagers.forEach((manager, idx) => {
        const displayRank = manager.rank || (idx + 1);
        podiumHTML += `
            <div class="manager-card rank-${displayRank}">
                <div class="card-rank">${displayRank}</div>
                <div class="card-content">
                    <div class="card-team-name">${manager.entry_name}</div>
                    <div class="card-manager">${manager.player_name}</div>
                    <div class="card-stats">
                        <div class="stat-group">
                            <span class="stat-label">GW Pts</span>
                            <span class="stat-value">${manager.event_total}</span>
                        </div>
                        <div class="stat-group">
                            <span class="stat-label">Total</span>
                            <span class="stat-value" style="color: var(--fpl-purple);">${manager.total}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    podiumContainer.innerHTML = podiumHTML;
}

function renderChart(standings) {
    const container = document.getElementById('chart-container');
    if (!container) return;

    const hasHistory = standings.length > 0 && 
                       standings[0].gw_history && 
                       standings[0].gw_history.length > 0;

    if (!hasHistory) {
        container.innerHTML = `
            <div style="display:flex; align-items:center; justify-content:center; height:100%; color:#6b7280; font-weight:600; text-align:center; padding: 2rem;">
                📈 The Points Race graph will populate automatically after Gameweek 1 points are updated!
            </div>
        `;
        return;
    }

    const canvas = document.getElementById('pointsChart');
    if (!canvas) return;

    const existingChart = Chart.getChart(canvas);
    if (existingChart) existingChart.destroy();

    const ctx = canvas.getContext('2d');
    const labels = standings[0].gw_history.map((_, i) => `GW ${i + 1}`);
    const colors = ['#00ff87', '#02efff', '#ff2882', '#37003c', '#eab308', '#a855f7', '#3b82f6', '#f97316'];
    
    const datasets = standings.slice(0, 8).map((manager, i) => ({
        label: manager.entry_name,
        data: manager.gw_history,
        borderColor: colors[i % colors.length],
        backgroundColor: colors[i % colors.length],
        tension: 0.3,
        borderWidth: 2,
        pointRadius: 3,
        fill: false
    }));

    new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top' } }
        }
    });
}