const entries = Array.isArray(window.JUST404IT_PORTFOLIO) ? window.JUST404IT_PORTFOLIO : [];
const grid = document.querySelector("#portfolio-grid");
const search = document.querySelector("#search");
const summary = document.querySelector("#result-summary");
const sort = document.querySelector("#sort");
const year = document.querySelector("#year");
const reset = document.querySelector("#reset-filters");
const facets = [...document.querySelectorAll(".facet")];

const state = {
  status: "all",
  formats: new Set(),
  contexts: new Set(),
  platforms: new Set(),
};

function clean(value) {
  return String(value || "");
}

function html(value) {
  return clean(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

function initials(title) {
  return clean(title).split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function intersects(values, selected) {
  return selected.size === 0 || (values || []).some((value) => selected.has(value));
}

function matches(entry) {
  if (state.status === "playable" && !entry.playable) return false;
  if (state.status === "recognized" && !entry.hasAccolade) return false;
  if (!intersects(entry.formats, state.formats)) return false;
  if (!intersects(entry.contexts, state.contexts)) return false;
  if (!intersects(entry.platforms, state.platforms)) return false;
  if (year.value !== "all" && entry.year !== year.value) return false;

  const query = clean(search.value).trim().toLowerCase();
  if (!query) return true;
  const haystack = [
    entry.title,
    entry.year,
    entry.description,
    ...(entry.categories || []),
    ...(entry.details || []),
    ...(entry.credits || []),
    ...(entry.accolades || []),
  ].join(" ").toLowerCase();
  return haystack.includes(query);
}

function seriesValue(entry, fallback) {
  const numbers = entry.gameNumbers || [];
  return numbers.length ? Math.max(...numbers) : fallback;
}

function sortEntries(list) {
  const sorted = [...list];
  const mode = sort.value;
  sorted.sort((a, b) => {
    if (mode === "series-asc") return seriesValue(a, 999) - seriesValue(b, 999) || a.title.localeCompare(b.title);
    if (mode === "newest") return clean(b.year).localeCompare(clean(a.year)) || seriesValue(b, 0) - seriesValue(a, 0);
    if (mode === "oldest") return clean(a.year).localeCompare(clean(b.year)) || seriesValue(a, 999) - seriesValue(b, 999);
    if (mode === "title") return a.title.localeCompare(b.title);
    return seriesValue(b, 0) - seriesValue(a, 0) || a.title.localeCompare(b.title);
  });
  return sorted;
}

function tag(label, className = "") {
  return `<span class="tag ${className}">${html(label)}</span>`;
}

function categoryTags(entry) {
  const tags = [];
  (entry.categories || []).forEach((category) => {
    if (/^20\d{2}$/.test(category)) return;
    if (category === "Digital") tags.push(tag(category, "tag-format-digital"));
    else if (category === "Analog") tags.push(tag(category, "tag-format-analog"));
    else if (category === "Intermedia Games") tags.push(tag("Intermedia", "tag-format-intermedia"));
    else if (category === "Award Winning" || category === "Exhibited") tags.push(tag(category, "tag-recognition"));
    else if (tags.length < 5) tags.push(tag(category));
  });
  if (entry.playable) tags.push(tag("Playable", "tag-playable"));
  return tags.slice(0, 6).join("");
}

function renderCard(entry) {
  const format = (entry.formats || ["other"])[0] || "other";
  const thumb = entry.image
    ? `<img src="${html(entry.image)}" alt="">`
    : `<span class="fallback-thumb" aria-hidden="true">${html(initials(entry.title))}</span>`;
  const links = (entry.links || []).filter((link) => /play|download|itch|game jolt|newgrounds|rules/i.test(link.label)).slice(0, 2);
  const linkMarkup = links.map((link) => `<a href="${html(link.url)}">${html(link.label)}</a>`).join("");
  return `<article class="portfolio-card" data-format="${html(format)}">
    <div class="thumb">${thumb}</div>
    <div class="portfolio-body">
      <span class="meta">${html(entry.year || "Archive")} · ${html(entry.seriesLabel)}</span>
      <h3><a href="${html(entry.detailPath)}">${html(entry.title)}</a></h3>
      <p>${html(entry.description || "A project from the 100 Games in 5 Years archive.")}</p>
      <div class="tags">${categoryTags(entry)}</div>
      <div class="card-links"><a class="details-link" href="${html(entry.detailPath)}">Project page</a>${linkMarkup}</div>
    </div>
  </article>`;
}

function updateFacetState() {
  facets.forEach((facet) => {
    const group = facet.dataset.group;
    const value = facet.dataset.value;
    const active = group === "status" ? state.status === value : state[group].has(value);
    facet.classList.toggle("is-active", active);
    facet.setAttribute("aria-pressed", String(active));
  });
}

function syncUrl() {
  const params = new URLSearchParams();
  const query = clean(search.value).trim();
  if (query) params.set("q", query);
  if (state.status !== "all") params.set("status", state.status);
  ["formats", "contexts", "platforms"].forEach((group) => {
    if (state[group].size) params.set(group, [...state[group]].join(","));
  });
  if (year.value !== "all") params.set("year", year.value);
  if (sort.value !== "series-desc") params.set("sort", sort.value);
  const queryString = params.toString();
  history.replaceState(null, "", `${location.pathname}${queryString ? `?${queryString}` : ""}${location.hash}`);
}

function render() {
  const visible = sortEntries(entries.filter(matches));
  const representedGames = new Set(visible.flatMap((entry) => entry.gameNumbers || [])).size;
  const projectWord = visible.length === 1 ? "project page" : "project pages";
  const gameWord = representedGames === 1 ? "game" : "games";
  summary.innerHTML = `<span>${visible.length}</span> ${projectWord} · ${representedGames} ${gameWord} represented`;
  grid.innerHTML = visible.length ? visible.map(renderCard).join("") : `<p class="empty">No project pages match this combination.</p>`;
  updateFacetState();
  syncUrl();
}

function loadUrlState() {
  const params = new URLSearchParams(location.search);
  search.value = params.get("q") || "";
  state.status = ["all", "playable", "recognized"].includes(params.get("status")) ? params.get("status") : "all";
  ["formats", "contexts", "platforms"].forEach((group) => {
    clean(params.get(group)).split(",").filter(Boolean).forEach((value) => state[group].add(value));
  });
  if ([...year.options].some((option) => option.value === params.get("year"))) year.value = params.get("year");
  if ([...sort.options].some((option) => option.value === params.get("sort"))) sort.value = params.get("sort");
}

facets.forEach((facet) => {
  facet.addEventListener("click", () => {
    const group = facet.dataset.group;
    const value = facet.dataset.value;
    if (group === "status") state.status = value;
    else if (state[group].has(value)) state[group].delete(value);
    else state[group].add(value);
    render();
  });
});

search.addEventListener("input", render);
sort.addEventListener("change", render);
year.addEventListener("change", render);
reset.addEventListener("click", () => {
  search.value = "";
  sort.value = "series-desc";
  year.value = "all";
  state.status = "all";
  state.formats.clear();
  state.contexts.clear();
  state.platforms.clear();
  render();
});

loadUrlState();
render();
