const entries = Array.isArray(window.JUST404IT_PORTFOLIO) ? window.JUST404IT_PORTFOLIO : [];
const grid = document.querySelector("#portfolio-grid");
const search = document.querySelector("#search");
const count = document.querySelector("#visible-count");
const filters = [...document.querySelectorAll(".filter")];
let activeFilter = "all";

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

function matchesFilter(entry) {
  if (activeFilter === "all") return true;
  if (activeFilter === "playable") return Boolean(entry.playable);
  if (activeFilter === "accolade") return Boolean(entry.hasAccolade);
  const haystack = [...(entry.categories || []), ...(entry.details || [])].join(" ").toLowerCase();
  return haystack.includes(activeFilter);
}

function matchesSearch(entry) {
  const query = clean(search.value).trim().toLowerCase();
  if (!query) return true;
  const haystack = [
    entry.title,
    entry.year,
    entry.description,
    ...(entry.categories || []),
    ...(entry.details || []),
  ].join(" ").toLowerCase();
  return haystack.includes(query);
}

function initials(title) {
  return clean(title)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function renderCard(entry) {
  const categories = (entry.categories || []).slice(0, 4);
  const links = (entry.links || []).slice(0, 2);
  const meta = [entry.year, entry.gameNumber ? `Game ${entry.gameNumber}/100` : "", entry.developmentTime]
    .filter(Boolean)
    .join(" · ");
  const thumb = entry.image
    ? `<img src="${html(entry.image)}" alt="">`
    : `<span class="fallback-thumb">${html(initials(entry.title))}</span>`;
  const linkMarkup = links.map((link) => `<a href="${html(link.url)}">${html(link.label)}</a>`).join("");
  const archiveLink = `<a href="${html(entry.sourceUrl)}">Original</a>`;
  return `<article class="portfolio-card">
    <div class="thumb">${thumb}</div>
    <div class="portfolio-body">
      <span class="meta">${html(meta || "Archive Entry")}</span>
      <h3>${html(entry.title)}</h3>
      <p>${html(entry.description || "Recovered from the JUSTDELETEIT WordPress archive.")}</p>
      <div class="tags">${categories.map((category) => `<span class="tag">${html(category)}</span>`).join("")}</div>
      <div class="card-links">${linkMarkup}${archiveLink}</div>
    </div>
  </article>`;
}

function render() {
  const visible = entries.filter((entry) => matchesFilter(entry) && matchesSearch(entry));
  count.textContent = visible.length;
  grid.innerHTML = visible.length
    ? visible.map(renderCard).join("")
    : `<p class="empty">No archive entries match that search.</p>`;
}

filters.forEach((filter) => {
  filter.addEventListener("click", () => {
    activeFilter = filter.dataset.filter;
    filters.forEach((item) => item.classList.toggle("is-active", item === filter));
    render();
  });
});

search.addEventListener("input", render);
render();
