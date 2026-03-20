const form = document.getElementById("analyze-form");
const output = document.getElementById("output");
const submitBtn = document.getElementById("submit-btn");
const viewBtn = document.getElementById("view-btn");

function render(data) {
  output.textContent = JSON.stringify(data, null, 2);
}

function extractPlaylistIdFromUrl(value) {
  const input = (value || "").trim();
  if (!input) return "";

  try {
    const parsed = new URL(input);
    return parsed.searchParams.get("list") || "";
  } catch {
    return "";
  }
}

viewBtn.addEventListener("click", () => {
  const url = document.getElementById("url").value.trim();
  const playlistId = extractPlaylistIdFromUrl(url);

  if (!playlistId) {
    render({ error: "Playlist link must contain a valid list parameter (playlist ID)." });
    return;
  }

  window.open(`/playlist/${encodeURIComponent(playlistId)}/view`, "_blank");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const url = document.getElementById("url").value.trim();
  const freshness = document.getElementById("freshness").value.trim();

  if (!url) {
    render({ error: "Playlist URL is required." });
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Analyzing...";

  try {
    const query = new URLSearchParams({
      url,
      freshness_hours: freshness || "24",
    });

    const response = await fetch(`/analyze?${query.toString()}`, {
      method: "POST",
    });

    const data = await response.json();
    if (!response.ok) {
      render({ status: response.status, ...data });
      return;
    }

    render(data);
  } catch (error) {
    render({ error: error.message || "Request failed" });
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Analyze";
  }
});
