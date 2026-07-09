const entries = Array.isArray(window.JUST404IT_PORTFOLIO) ? window.JUST404IT_PORTFOLIO : [];
const grid = document.querySelector("#portfolio-grid");
const search = document.querySelector("#search");
const summary = document.querySelector("#result-summary");
const sort = document.querySelector("#sort");
const year = document.querySelector("#year");
const reset = document.querySelector("#reset-filters");
const surprise = document.querySelector("#surprise-me");
const activeFilters = document.querySelector("#active-filters");
const activeFilterList = document.querySelector("#active-filter-list");
const facets = [...document.querySelectorAll(".facet")];
const routes = [...document.querySelectorAll("[data-preset]")];
const moreFilters = document.querySelector(".more-filters");
const multiGroups = ["formats", "contexts", "platforms", "recognition", "access", "pace"];
let visibleEntries = [];

const state = {
  status: "all",
  formats: new Set(),
  contexts: new Set(),
  platforms: new Set(),
  recognition: new Set(),
  access: new Set(),
  pace: new Set(),
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

function matches(entry, ignoreGroup = "") {
  if (ignoreGroup !== "status" && state.status === "playable" && !entry.playable) return false;
  if (ignoreGroup !== "status" && state.status === "recognized" && !entry.hasAccolade) return false;
  if (ignoreGroup !== "formats" && !intersects(entry.formats, state.formats)) return false;
  if (ignoreGroup !== "contexts" && !intersects(entry.contexts, state.contexts)) return false;
  if (ignoreGroup !== "platforms" && !intersects(entry.platforms, state.platforms)) return false;
  if (ignoreGroup !== "recognition" && !intersects(entry.recognition, state.recognition)) return false;
  if (ignoreGroup !== "access" && !intersects(entry.access, state.access)) return false;
  if (ignoreGroup !== "pace" && state.pace.size && !state.pace.has(entry.developmentPace)) return false;
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
    entry.developmentTime,
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
    if (mode === "fastest" || mode === "longest") {
      const aKnown = Number.isFinite(a.developmentDays);
      const bKnown = Number.isFinite(b.developmentDays);
      if (aKnown !== bKnown) return aKnown ? -1 : 1;
      if (aKnown && a.developmentDays !== b.developmentDays) {
        return mode === "fastest" ? a.developmentDays - b.developmentDays : b.developmentDays - a.developmentDays;
      }
      return seriesValue(b, 0) - seriesValue(a, 0);
    }
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
    const count = entries.filter((entry) => {
      if (!matches(entry, group)) return false;
      if (group === "status") {
        if (value === "all") return true;
        if (value === "playable") return entry.playable;
        return entry.hasAccolade;
      }
      if (group === "pace") return entry.developmentPace === value;
      return (entry[group] || []).includes(value);
    }).length;
    const countNode = facet.querySelector("span");
    if (countNode) countNode.textContent = count;
    facet.disabled = count === 0 && !active;
  });
}

function facetLabel(facet) {
  return [...facet.childNodes].find((node) => node.nodeType === Node.TEXT_NODE)?.textContent.trim() || facet.dataset.value;
}

function activeChip(label, group, value = "") {
  return `<button class="active-filter" type="button" data-remove-group="${html(group)}" data-remove-value="${html(value)}" aria-label="Remove ${html(label)} filter">${html(label)} ×</button>`;
}

function updateActiveFilters() {
  const chips = [];
  if (state.status !== "all") {
    const facet = facets.find((item) => item.dataset.group === "status" && item.dataset.value === state.status);
    chips.push(activeChip(facetLabel(facet), "status", state.status));
  }
  multiGroups.forEach((group) => {
    state[group].forEach((value) => {
      const facet = facets.find((item) => item.dataset.group === group && item.dataset.value === value);
      chips.push(activeChip(facetLabel(facet), group, value));
    });
  });
  if (year.value !== "all") chips.push(activeChip(year.value, "year", year.value));
  const query = clean(search.value).trim();
  if (query) chips.push(activeChip(`Search: ${query}`, "search"));
  activeFilterList.innerHTML = chips.join("");
  activeFilters.hidden = chips.length === 0;
}

function syncUrl() {
  const params = new URLSearchParams();
  const query = clean(search.value).trim();
  if (query) params.set("q", query);
  if (state.status !== "all") params.set("status", state.status);
  multiGroups.forEach((group) => {
    if (state[group].size) params.set(group, [...state[group]].join(","));
  });
  if (year.value !== "all") params.set("year", year.value);
  if (sort.value !== "series-desc") params.set("sort", sort.value);
  const queryString = params.toString();
  history.replaceState(null, "", `${location.pathname}${queryString ? `?${queryString}` : ""}${location.hash}`);
}

function render() {
  visibleEntries = sortEntries(entries.filter((entry) => matches(entry)));
  const representedGames = new Set(visibleEntries.flatMap((entry) => entry.gameNumbers || [])).size;
  const projectWord = visibleEntries.length === 1 ? "project page" : "project pages";
  const gameWord = representedGames === 1 ? "game" : "games";
  summary.innerHTML = `<span>${visibleEntries.length}</span> ${projectWord} · ${representedGames} ${gameWord} represented`;
  grid.innerHTML = visibleEntries.length ? visibleEntries.map(renderCard).join("") : `<p class="empty">Nothing lives at this exact intersection. Yet.</p>`;
  surprise.disabled = visibleEntries.length === 0;
  updateFacetState();
  updateActiveFilters();
  syncUrl();
}

function loadUrlState() {
  const params = new URLSearchParams(location.search);
  search.value = params.get("q") || "";
  state.status = ["all", "playable", "recognized"].includes(params.get("status")) ? params.get("status") : "all";
  multiGroups.forEach((group) => {
    const allowed = new Set(facets.filter((item) => item.dataset.group === group).map((item) => item.dataset.value));
    clean(params.get(group)).split(",").filter((value) => allowed.has(value)).forEach((value) => state[group].add(value));
  });
  if ([...year.options].some((option) => option.value === params.get("year"))) year.value = params.get("year");
  if ([...sort.options].some((option) => option.value === params.get("sort"))) sort.value = params.get("sort");
  if (moreFilters && ["recognition", "access", "pace"].some((group) => state[group].size)) moreFilters.open = true;
}

function clearFilters(resetSort = true) {
  search.value = "";
  if (resetSort) sort.value = "series-desc";
  year.value = "all";
  state.status = "all";
  multiGroups.forEach((group) => state[group].clear());
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
  clearFilters();
  render();
});

routes.forEach((route) => {
  route.addEventListener("click", () => {
    clearFilters();
    const preset = route.dataset.preset;
    if (preset === "play-now") {
      state.status = "playable";
      state.access.add("online");
    } else if (preset === "nonsense") state.contexts.add("silly");
    else if (preset === "serious") state.contexts.add("serious");
    else if (preset === "off-screen") {
      state.formats.add("analog");
      state.formats.add("intermedia");
    } else if (preset === "made-fast") state.pace.add("day-or-less");
    else if (preset === "decorated") state.recognition.add("award-winning");
    if (moreFilters && ["made-fast", "decorated"].includes(preset)) moreFilters.open = true;
    render();
  });
});

activeFilterList.addEventListener("click", (event) => {
  const chip = event.target.closest("[data-remove-group]");
  if (!chip) return;
  const group = chip.dataset.removeGroup;
  const value = chip.dataset.removeValue;
  if (group === "status") state.status = "all";
  else if (group === "year") year.value = "all";
  else if (group === "search") search.value = "";
  else if (state[group]) state[group].delete(value);
  render();
});

surprise.addEventListener("click", () => {
  if (!visibleEntries.length) return;
  const random = new Uint32Array(1);
  crypto.getRandomValues(random);
  const entry = visibleEntries[random[0] % visibleEntries.length];
  location.href = entry.detailPath;
});

loadUrlState();
render();
