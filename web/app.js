const briefing = document.querySelector("#briefing");
const newZealand = document.querySelector("#new-zealand");
const government = document.querySelector("#government");
const sports = document.querySelector("#sports");
const generated = document.querySelector("#generated");
const drawer = document.querySelector("#drawer");
const closeDrawer = document.querySelector("#closeDrawer");
const drawerSource = document.querySelector("#drawerSource");
const drawerTitle = document.querySelector("#drawerTitle");
const drawerDescription = document.querySelector("#drawerDescription");
const drawerLink = document.querySelector("#drawerLink");
const articleExcerpt = document.querySelector("#articleExcerpt");
const relatedList = document.querySelector("#relatedList");

let storiesById = new Map();
let governmentById = new Map();
let sportsById = new Map();
let activeDrawerItem = "";

const collapsedStorageKey = "modernCommunityTopics.collapsedSections";
const defaultCollapsedSections = new Set(["score:sports-premier-league"]);

async function loadBriefing() {
  try {
    const [response, governmentResponse, sportsResponse] = await Promise.all([
      fetch("../data/latest.json", { cache: "no-store" }),
      fetch("../data/government.json", { cache: "no-store" }),
      fetch("../data/sports.json", { cache: "no-store" })
    ]);
    if (!response.ok) throw new Error(`Could not load briefing: ${response.status}`);
    const data = await response.json();
    const governmentData = governmentResponse.ok ? await governmentResponse.json() : { sections: [] };
    const sportsData = sportsResponse.ok ? await sportsResponse.json() : { scoreboards: [], sections: [] };
    renderBriefing(data);
    renderGovernment(governmentData);
    renderSports(sportsData);
    renderNewZealand(data, governmentData, sportsData);
  } catch (error) {
    briefing.innerHTML = `
      <div class="error">
        Run <code>python3 scripts/fetch_news.py</code> first, then refresh this page.
      </div>
    `;
    generated.textContent = "No briefing yet";
    newZealand.innerHTML = "";
    government.innerHTML = "";
    sports.innerHTML = "";
  }
}

function renderBriefing(data) {
  generated.textContent = `Updated ${data.generatedAtLocal}`;
  storiesById = new Map();

  briefing.innerHTML = (data.sections || [])
    .filter((section) => !section.id.startsWith("new-zealand"))
    .map((section) => renderNewsSection(section, "news"))
    .join("");

  attachNewsStoryHandlers(briefing);
  attachCollapseHandlers(briefing);
}

function renderNewZealand(data, governmentData, sportsData) {
  const newsSections = (data.sections || [])
    .filter((section) => section.id === "new-zealand" || section.id === "new-zealand-politics")
    .map((section) => renderNewsSection(section, "new-zealand"));
  const governmentSections = (governmentData.sections || [])
    .filter((section) => section.id === "new-zealand-government")
    .map((section) => renderGovernmentSection(section, "new-zealand-government"));
  const sportsSections = (sportsData.sections || [])
    .filter((section) => section.id === "new-zealand-sports")
    .map((section) => renderSportsSection(section, "new-zealand"));

  newZealand.innerHTML = [...newsSections, ...governmentSections, ...sportsSections].join("") || `
    <article class="section">
      <h2>New Zealand</h2>
      <p class="focus">No New Zealand stories were found in this refresh.</p>
    </article>
  `;

  attachNewsStoryHandlers(newZealand);
  newZealand.querySelectorAll("button[data-sports-id]").forEach((button) => {
    attachStoryButton(button, button.dataset.sportsId, sportsById, openSportsItem, "sports");
  });
  newZealand.querySelectorAll("button[data-government-id]").forEach((button) => {
    attachStoryButton(button, button.dataset.governmentId, governmentById, openGovernmentItem, "government");
  });
  attachCollapseHandlers(newZealand);
}

function renderNewsSection(section, namespace) {
  const items = section.items || [];
  const stories = items.length
    ? items.map((item) => {
        storiesById.set(item.id, item);
        return `
          <li class="story">
            <button data-id="${escapeHtml(item.id)}">
              <span class="story-title">${escapeHtml(item.title)}</span>
              <span class="story-meta">${escapeHtml(item.source)}${formatDate(item.published)}</span>
            </button>
          </li>
        `;
      }).join("")
    : `<li class="empty">No current stories found.</li>`;

  const collapseId = `${namespace}:${section.id}`;
  const collapsed = isCollapsed(collapseId);

  return `
    <article class="section collapsible-section ${collapsed ? "is-collapsed" : ""}" data-collapse-id="${escapeHtml(collapseId)}">
      <div class="section-heading">
        <div>
          <h2>${escapeHtml(section.name)}</h2>
          <p class="focus">${escapeHtml(section.focus || "")}</p>
        </div>
        ${collapseButton(collapseId, collapsed, section.name)}
      </div>
      <div class="collapsible-body">
        <ul class="stories">${stories}</ul>
      </div>
    </article>
  `;
}

function attachNewsStoryHandlers(root) {
  root.querySelectorAll("button[data-id]").forEach((button) => {
    attachStoryButton(button, button.dataset.id, storiesById, openStory, "story");
  });
}

function renderGovernment(data) {
  governmentById = new Map();
  const highlights = renderGovernmentHighlights(data.highlights || {});
  const sections = (data.sections || [])
    .filter((section) => section.id !== "new-zealand-government")
    .map((section) => renderGovernmentSection(section, "government"))
    .join("");

  government.innerHTML = `${highlights}${sections}`;

  government.querySelectorAll("button[data-government-id]").forEach((button) => {
    attachStoryButton(button, button.dataset.governmentId, governmentById, openGovernmentItem, "government");
  });
  attachCollapseHandlers(government);
}

function renderGovernmentSection(section, namespace) {
  const items = section.items || [];
  const cards = items.length
    ? items.map((item) => {
        governmentById.set(item.id, item);
        return `
          <li class="story">
            <button data-government-id="${escapeHtml(item.id)}">
              <span class="story-title">${escapeHtml(item.title)}</span>
              <span class="story-meta">${escapeHtml(item.status || item.source)}</span>
            </button>
          </li>
        `;
      }).join("")
    : `<li class="empty">No current government items found.</li>`;

  const collapseId = `${namespace}:${section.id}`;
  const collapsed = isCollapsed(collapseId);

  return `
    <article class="section collapsible-section ${collapsed ? "is-collapsed" : ""}" data-collapse-id="${escapeHtml(collapseId)}">
      <div class="section-heading">
        <div>
          <h2>${escapeHtml(section.name)}</h2>
          <p class="focus">${escapeHtml(section.focus || "")}</p>
        </div>
        ${collapseButton(collapseId, collapsed, section.name)}
      </div>
      <div class="collapsible-body">
        <ul class="stories">${cards}</ul>
      </div>
    </article>
  `;
}

function renderGovernmentHighlights(highlights) {
  const policyWatch = highlights.policyWatch || [];
  const important = highlights.important || [];
  const passed = highlights.passed || [];
  const notPassed = highlights.notPassed || [];

  const summaryGroup = (title, items, emptyText) => {
    const collapseId = `government-highlight:${stableKey(title)}`;
    const collapsed = isCollapsed(collapseId);
    return `
    <article class="section government-summary collapsible-section ${collapsed ? "is-collapsed" : ""}" data-collapse-id="${escapeHtml(collapseId)}">
      <div class="section-heading">
        <div>
          <h2>${escapeHtml(title)}</h2>
        </div>
        ${collapseButton(collapseId, collapsed, title)}
      </div>
      <div class="collapsible-body">
        <ul class="stories">
        ${items.length ? items.map((item) => {
          governmentById.set(item.id, item);
          return `
            <li class="story">
              <button data-government-id="${escapeHtml(item.id)}">
                <span class="story-title">${escapeHtml(item.title)}</span>
                <span class="story-meta">${escapeHtml(formatGovernmentMeta(item))}</span>
                <span class="story-reason">${escapeHtml((item.importanceReasons || []).join(" "))}</span>
              </button>
            </li>
          `;
        }).join("") : `<li class="empty">${escapeHtml(emptyText)}</li>`}
        </ul>
      </div>
    </article>
  `;
  };

  return `
    <section class="government-overview">
      ${summaryGroup("Policy Watch", policyWatch, "No high-impact policy stories matched this refresh.")}
      ${summaryGroup("Most Relevant", important, "No parsed bill highlights yet; use the official tracker links below.")}
      ${summaryGroup("Became Law", passed, "No new enacted bills were detected from the official trackers this refresh.")}
      ${summaryGroup("Stopped or Stalled", notPassed, "No defeated, withdrawn, or stalled bills were detected from the official trackers this refresh.")}
    </section>
  `;
}

function renderSports(data) {
  sportsById = new Map();
  const scoreboards = data.scoreboards || [];
  const scoreboardCards = scoreboards.length
    ? scoreboards.map((item) => {
        sportsById.set(item.id, item);
        const collapseId = `score:${item.id}`;
        const collapsed = isCollapsed(collapseId);
        return `
          <li class="story score-card ${collapsed ? "is-collapsed" : ""}" data-collapse-id="${escapeHtml(collapseId)}">
            <div class="score-card-shell">
              <div class="collapsible-heading">
                <button class="score-button score-main-button" data-sports-id="${escapeHtml(item.id)}">
                  <span class="story-title">${escapeHtml(item.title)}</span>
                  <span class="story-meta">${escapeHtml(item.status)} / ${escapeHtml(item.source)}</span>
                </button>
                ${collapseButton(collapseId, collapsed, item.title)}
              </div>
              <div class="collapsible-body">
                ${renderScoreBullets(item)}
              </div>
            </div>
          </li>
        `;
      }).join("")
    : `<li class="empty">No score trackers configured.</li>`;

  const sections = (data.sections || [])
    .filter((section) => section.id !== "new-zealand-sports")
    .map((section) => renderSportsSection(section, "section"))
    .join("");

  const scoresCollapseId = "sports:scores-fixtures";
  const scoresCollapsed = isCollapsed(scoresCollapseId);

  sports.innerHTML = `
    <article class="section collapsible-section ${scoresCollapsed ? "is-collapsed" : ""}" data-collapse-id="${escapeHtml(scoresCollapseId)}">
      <div class="section-heading">
        <div>
          <h2>Scores & Fixtures</h2>
          <p class="focus">Official scoreboards for the competitions you care about</p>
        </div>
        ${collapseButton(scoresCollapseId, scoresCollapsed, "Scores & Fixtures")}
      </div>
      <div class="collapsible-body">
        <ul class="stories">${scoreboardCards}</ul>
      </div>
    </article>
    ${sections}
  `;

  sports.querySelectorAll("button[data-sports-id]").forEach((button) => {
    attachStoryButton(button, button.dataset.sportsId, sportsById, openSportsItem, "sports");
  });
  attachCollapseHandlers(sports);
}

function renderSportsSection(section, namespace) {
  const items = section.items || [];
  const cards = items.length
    ? items.map((item) => {
        sportsById.set(item.id, item);
        return `
          <li class="story">
            <button data-sports-id="${escapeHtml(item.id)}">
              <span class="story-title">${escapeHtml(item.title)}</span>
              <span class="story-meta">${escapeHtml(item.source)}${formatDate(item.published)}</span>
            </button>
          </li>
        `;
      }).join("")
    : `<li class="empty">No current sports headlines found.</li>`;
  const collapseId = `${namespace}:${section.id}`;
  const collapsed = isCollapsed(collapseId);

  return `
    <article class="section collapsible-section ${collapsed ? "is-collapsed" : ""}" data-collapse-id="${escapeHtml(collapseId)}">
      <div class="section-heading">
        <div>
          <h2>${escapeHtml(section.name)}</h2>
          <p class="focus">${escapeHtml(section.focus || "")}</p>
        </div>
        ${collapseButton(collapseId, collapsed, section.name)}
      </div>
      <div class="collapsible-body">
        <ul class="stories">${cards}</ul>
      </div>
    </article>
  `;
}

function renderScoreBullets(item) {
  const matches = item.matches || [];
  if (!matches.length) {
    return `
      <ul class="score-bullets">
        <li>Open the official tracker for current scores and fixtures.</li>
      </ul>
    `;
  }
  return `
    <ul class="score-bullets">
      ${matches.map((match) => `
        <li>
          <span class="score-line">${escapeHtml(match.text)}</span>
          ${match.note ? `<span class="score-note">${escapeHtml(match.note)}</span>` : ""}
        </li>
      `).join("")}
    </ul>
    <span class="score-source">Scores via ${escapeHtml(item.scoreSource || item.source || "official tracker")}</span>
  `;
}

function collapseButton(id, collapsed, label) {
  return `
    <button
      class="collapse-toggle"
      data-collapse-toggle="${escapeHtml(id)}"
      aria-expanded="${collapsed ? "false" : "true"}"
      aria-label="${collapsed ? "Show" : "Hide"} ${escapeHtml(label)}"
      title="${collapsed ? "Show" : "Hide"} ${escapeHtml(label)}"
    >
      ${collapsed ? "+" : "-"}
    </button>
  `;
}

function attachCollapseHandlers(root) {
  root.querySelectorAll("button[data-collapse-toggle]").forEach((button) => {
    button.addEventListener("click", () => toggleCollapse(button.dataset.collapseToggle));
  });
}

function attachStoryButton(button, id, sourceMap, openHandler, namespace) {
  button.addEventListener("click", (event) => {
    if (event.metaKey || event.ctrlKey) {
      openSource(sourceMap.get(id));
      return;
    }
    openHandler(id);
  });
  button.addEventListener("auxclick", (event) => {
    if (event.button !== 1) return;
    event.preventDefault();
    openSource(sourceMap.get(id));
  });
  button.dataset.drawerKey = `${namespace}:${id}`;
}

function getCollapsedSections() {
  try {
    const saved = localStorage.getItem(collapsedStorageKey);
    if (!saved) return new Set(defaultCollapsedSections);
    const parsed = JSON.parse(saved);
    return new Set(Array.isArray(parsed) ? parsed : []);
  } catch (error) {
    return new Set(defaultCollapsedSections);
  }
}

function saveCollapsedSections(collapsed) {
  try {
    localStorage.setItem(collapsedStorageKey, JSON.stringify([...collapsed]));
  } catch (error) {
    // The UI still works for this session if browser storage is unavailable.
  }
}

function isCollapsed(id) {
  return getCollapsedSections().has(id);
}

function toggleCollapse(id) {
  if (!id) return;
  const collapsed = getCollapsedSections();
  const shouldCollapse = !collapsed.has(id);
  if (shouldCollapse) {
    collapsed.add(id);
  } else {
    collapsed.delete(id);
  }
  saveCollapsedSections(collapsed);

  const target = document.querySelector(`[data-collapse-id="${cssEscape(id)}"]`);
  if (!target) return;
  target.classList.toggle("is-collapsed", shouldCollapse);
  const button = target.querySelector(`[data-collapse-toggle="${cssEscape(id)}"]`);
  if (button) {
    const label = button.getAttribute("aria-label")?.replace(/^(Show|Hide)\s+/, "") || "section";
    button.textContent = shouldCollapse ? "+" : "-";
    button.setAttribute("aria-expanded", shouldCollapse ? "false" : "true");
    button.setAttribute("aria-label", `${shouldCollapse ? "Show" : "Hide"} ${label}`);
    button.setAttribute("title", `${shouldCollapse ? "Show" : "Hide"} ${label}`);
  }
}

function openStory(id) {
  const story = storiesById.get(id);
  if (!story) return;
  if (toggleDrawerClosed(`story:${id}`)) return;

  drawerSource.textContent = `${story.sectionName} / ${story.source}`;
  drawerTitle.textContent = story.title;
  drawerDescription.textContent = story.description ? "Source-provided excerpt below." : "No source excerpt was provided by the feed.";
  drawerLink.href = story.url;
  articleExcerpt.innerHTML = story.description
    ? `<h3>Source Excerpt</h3><p>${escapeHtml(story.description)}</p>`
    : `<h3>Source Excerpt</h3><p>The feed did not provide an excerpt. Open the original story for the full article.</p>`;

  const related = story.relatedSources || [];
  relatedList.innerHTML = related.length
    ? related.map((item) => `
        <li><a href="${escapeHtml(item.url)}">${escapeHtml(item.title)}</a><br><span>${escapeHtml(item.source)}${item.reason ? ` / ${escapeHtml(item.reason)}` : ""}</span></li>
      `).join("")
    : "<li>No strong related source found in today's feed set.</li>";

  showDrawer(`story:${id}`);
}

function openSportsItem(id) {
  const item = sportsById.get(id);
  if (!item) return;
  if (toggleDrawerClosed(`sports:${id}`)) return;

  drawerSource.textContent = `${item.source || "Sports"} / ${item.status || "Sports"}`;
  drawerTitle.textContent = item.title;
  drawerDescription.textContent = item.description ? "Source-provided excerpt below." : "Open the source for the latest scores, fixtures, or details.";
  drawerLink.href = item.url;
  articleExcerpt.innerHTML = item.description
    ? `<h3>Source Excerpt</h3><p>${escapeHtml(item.description)}</p>`
    : "";
  relatedList.innerHTML = `<li><a href="${escapeHtml(item.url)}">${escapeHtml(item.source || "Original source")}</a></li>`;

  showDrawer(`sports:${id}`);
}

function openGovernmentItem(id) {
  const item = governmentById.get(id);
  if (!item) return;
  if (toggleDrawerClosed(`government:${id}`)) return;

  drawerSource.textContent = `${item.source} / ${item.status || "Government"}`;
  drawerTitle.textContent = item.title;
  const reasons = item.importanceReasons?.length ? `\n\nWhy this matters: ${item.importanceReasons.join(" ")}` : "";
  drawerDescription.textContent = `${item.description || "Open the official source for current details."}${reasons}`;
  drawerLink.href = item.url;
  articleExcerpt.innerHTML = "";
  relatedList.innerHTML = `<li><a href="${escapeHtml(item.url)}">${escapeHtml(item.source)}</a></li>`;

  showDrawer(`government:${id}`);
}

function openSource(item) {
  if (!item?.url) return;
  window.open(item.url, "_blank", "noopener");
}

function toggleDrawerClosed(key) {
  if (!drawer.classList.contains("open") || activeDrawerItem !== key) {
    return false;
  }
  hideDrawer();
  return true;
}

function showDrawer(key) {
  activeDrawerItem = key;
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
}

function hideDrawer() {
  activeDrawerItem = "";
  drawer.classList.remove("open");
  drawer.setAttribute("aria-hidden", "true");
}

function formatGovernmentMeta(item) {
  return [item.status, item.category, item.sectionName].filter(Boolean).join(" / ");
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return ` / ${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
}

function stableKey(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function cssEscape(value) {
  if (window.CSS?.escape) {
    return CSS.escape(value);
  }
  return String(value).replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

closeDrawer.addEventListener("click", () => {
  hideDrawer();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    hideDrawer();
  }
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const view = tab.dataset.view;
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item === tab));
    document.querySelectorAll(".view").forEach((item) => item.classList.toggle("active", item.id === view || (view === "news" && item.id === "briefing")));
  });
});

loadBriefing();
setInterval(loadBriefing, 15 * 60 * 1000);
