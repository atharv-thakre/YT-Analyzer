const compareForm = document.getElementById("compare-form");
const compareBtn = document.getElementById("compare-btn");
const output = document.getElementById("output");
const summaryCard = document.getElementById("summary-card");
const summaryOutput = document.getElementById("summary-output");
const resultsGrid = document.getElementById("results-grid");

function renderRaw(data) {
  output.textContent = JSON.stringify(data, null, 2);
}

function formatNumber(value, digits = 2) {
  if (value == null) return "0";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = value;
}

function renderPlaylist(prefix, stats) {
  setText(`${prefix}-title`, stats.playlist_title || "Unknown Playlist");
  setText(`${prefix}-channel`, stats.playlist_channel || "Unknown Channel");
  setText(`${prefix}-total`, formatNumber(stats.total_videos, 0));
  setText(`${prefix}-views`, formatNumber(stats.avg_views));
  setText(`${prefix}-likes`, formatNumber(stats.avg_likes));
  setText(`${prefix}-comments`, formatNumber(stats.avg_comments));
  setText(`${prefix}-duration`, `${formatNumber(stats.avg_duration_sec)} sec`);
  setText(`${prefix}-engagement`, formatNumber(stats.engagement_avg, 4));
}

function winnerLabel(value) {
  if (value === "p1") return "Playlist 1";
  if (value === "p2") return "Playlist 2";
  return "Tie";
}

function extractPlaylistId(input) {
  const value = (input || "").trim();
  if (!value) return "";

  if (!value.startsWith("http://") && !value.startsWith("https://")) {
    return value;
  }

  try {
    const parsed = new URL(value);
    return parsed.searchParams.get("list") || "";
  } catch {
    return "";
  }
}

async function comparePlaylists(playlistId1, playlistId2) {
  const query = new URLSearchParams({ p1: playlistId1, p2: playlistId2 });
  const response = await fetch(`/compare-playlists?${query.toString()}`);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Failed to compare playlists");
  }

  return data;
}

compareForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const url1 = document.getElementById("url1").value.trim();
  const url2 = document.getElementById("url2").value.trim();
  if (!url1 || !url2) {
    renderRaw({ error: "Both playlist values are required." });
    return;
  }

  const p1 = extractPlaylistId(url1);
  const p2 = extractPlaylistId(url2);

  if (!p1 || !p2) {
    renderRaw({ error: "Could not extract playlist IDs. Provide valid URLs or playlist IDs." });
    return;
  }

  compareBtn.disabled = true;
  compareBtn.textContent = "Comparing...";

  try {
    const comparisonData = await comparePlaylists(p1, p2);

    renderPlaylist("p1", comparisonData.playlist_1);
    renderPlaylist("p2", comparisonData.playlist_2);

    const score = comparisonData.comparison.score;
    const overallWinner = comparisonData.comparison.overall_winner;

    summaryOutput.textContent = `Winner: ${winnerLabel(overallWinner)}\nScore: Playlist 1 = ${score.p1} | Playlist 2 = ${score.p2}`;
    summaryCard.hidden = false;
    resultsGrid.hidden = false;

    renderRaw({
      compare_input: { p1, p2 },
      comparison: comparisonData,
    });
  } catch (error) {
    summaryCard.hidden = true;
    resultsGrid.hidden = true;
    renderRaw({ error: error.message || "Request failed" });
  } finally {
    compareBtn.disabled = false;
    compareBtn.textContent = "Compare";
  }
});
