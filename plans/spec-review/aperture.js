"use strict";

(() => {
  const data = globalThis.ATTENTION_APERTURE_DATA;
  const select = (selector, root = document) => root.querySelector(selector);
  const selectAll = (selector, root = document) => [...root.querySelectorAll(selector)];

  const make = (tag, { className, text, attributes, dataset } = {}) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    if (attributes) Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
    if (dataset) Object.assign(node.dataset, dataset);
    return node;
  };

  const appendText = (selector, text) => {
    const node = select(selector);
    if (node) node.textContent = text;
  };

  const show = (selector) => {
    const node = select(selector);
    if (node) node.hidden = false;
  };

  const detailBlock = (title, { text, items, className = "" }) => {
    const block = make("div", { className: `detail-block ${className}`.trim() });
    block.append(make("h4", { text: title }));
    if (items) {
      const list = make("ul");
      items.forEach((item) => list.append(make("li", { text: item })));
      block.append(list);
    } else block.append(make("p", { text }));
    return block;
  };

  const buildReviewSlip = (reviewMarks) => {
    const reviewLabels = { agree: "looks right", discuss: "needs talk", change: "change course" };
    const lines = [
      `${data.artifact.title} — provisional capability review`,
      `reviewed ${reviewMarks.size} / ${data.capabilities.length}`,
      ""
    ];
    Object.entries(reviewLabels).forEach(([mark, label]) => {
      const marked = data.capabilities.filter(({ id }) => reviewMarks.get(id) === mark);
      lines.push(`${label} (${marked.length})`);
      lines.push(...(marked.length ? marked.map(({ name }) => `- ${name}`) : ["- none"]), "");
    });
    const unmarked = data.capabilities.filter(({ id }) => !reviewMarks.has(id));
    lines.push(`unmarked (${unmarked.length})`);
    lines.push(...(unmarked.length ? unmarked.map(({ name }) => `- ${name}`) : ["- none"]), "");
    lines.push("these are provisional review marks, not accepted decisions or implementation authority.");
    return lines.join("\n");
  };

  const copyText = async (text) => {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const fallback = make("textarea", { className: "visually-hidden", attributes: { readonly: "" } });
    const focused = document.activeElement;
    fallback.value = text;
    document.body.append(fallback);
    fallback.select();
    try {
      if (!document.execCommand("copy")) throw new Error("copy command refused");
    } finally {
      fallback.remove();
      focused?.focus({ preventScroll: true });
    }
  };

  const renderFoundations = () => {
    if (data.foundations.length === 0) return;
    show("[data-foundations-section]");
    const ledger = select("[data-foundations]");
    data.foundations.forEach((foundation) => {
      const item = make("article", { className: "foundation-item", dataset: { tone: foundation.tone } });
      item.append(make("span", { className: "foundation-mark", text: foundation.mark, attributes: { "aria-hidden": "true" } }));
      const copy = make("div");
      copy.append(make("strong", { text: foundation.title }), make("small", { text: foundation.copy }));
      item.append(copy);
      ledger.append(item);
    });
  };

  const renderCapabilities = () => {
    if (data.capabilities.length === 0) return;
    show("[data-capability-section]");
    const detail = select("[data-capability-detail]");
    const filterBar = select("[data-capability-filters]");
    const list = select("[data-capability-list]");
    const count = select("[data-review-count]");
    const fill = select("[data-review-fill]");
    const status = select("[data-review-status]");
    const copyButton = select("[data-copy-review]");
    const nextButton = select("[data-next-unmarked]");
    const reviewMarks = new Map();
    const reviewLabels = { agree: "looks right", discuss: "needs talk", change: "change course", unmarked: "unmarked" };
    const kinds = ["all", ...new Set(data.capabilities.map(({ kind }) => kind))];
    let activeId = data.capabilities[0].id;
    let activeFilter = "all";

    const visibleCapabilities = () => activeFilter === "all"
      ? data.capabilities
      : data.capabilities.filter(({ kind }) => kind === activeFilter);

    const updateProgress = () => {
      count.textContent = `${reviewMarks.size} / ${data.capabilities.length} marked`;
      fill.style.width = `${(reviewMarks.size / data.capabilities.length) * 100}%`;
      copyButton.disabled = reviewMarks.size === 0;
    };

    const renderList = () => {
      list.replaceChildren();
      visibleCapabilities().forEach((capability) => {
        const index = data.capabilities.indexOf(capability) + 1;
        const mark = reviewMarks.get(capability.id) || "unmarked";
        const button = make("button", {
          className: "capability-row",
          attributes: {
            type: "button",
            "aria-pressed": capability.id === activeId,
            "aria-label": `${capability.name}, ${capability.disposition}, ${reviewLabels[mark]}`
          },
          dataset: { capability: capability.id, reviewState: mark }
        });
        button.append(make("span", { className: "row-number", text: String(index).padStart(2, "0"), attributes: { "aria-hidden": "true" } }));
        const rowCopy = make("span", { className: "row-copy" });
        rowCopy.append(make("strong", { text: capability.name }), make("small", { text: capability.disposition }));
        button.append(rowCopy, make("span", { className: "review-dot", text: { agree: "✓", discuss: "?", change: "↺", unmarked: "" }[mark], attributes: { "aria-hidden": "true" } }));
        button.addEventListener("click", () => {
          activeId = capability.id;
          selectAll("[data-capability]", list).forEach((row) => row.setAttribute("aria-pressed", String(row.dataset.capability === activeId)));
          renderDetail();
        });
        const item = make("div", { attributes: { role: "listitem" } });
        item.append(button);
        list.append(item);
      });
    };

    const updateActionStates = () => {
      selectAll("[data-review-mark]", detail).forEach((button) => {
        button.setAttribute("aria-pressed", String(reviewMarks.get(activeId) === button.dataset.reviewMark));
      });
    };

    const markCapability = (mark) => {
      const capability = data.capabilities.find(({ id }) => id === activeId);
      if (reviewMarks.get(activeId) === mark) reviewMarks.delete(activeId);
      else reviewMarks.set(activeId, mark);
      renderList();
      updateActionStates();
      updateProgress();
      status.textContent = reviewMarks.has(activeId)
        ? `${capability.name}: ${reviewLabels[reviewMarks.get(activeId)]}.`
        : `${capability.name}: pencil mark cleared.`;
    };

    const renderDetail = () => {
      const capability = data.capabilities.find(({ id }) => id === activeId);
      const index = data.capabilities.indexOf(capability) + 1;
      const mark = reviewMarks.get(activeId) || "unmarked";
      detail.replaceChildren();
      const head = make("div", { className: "specimen-head" });
      head.append(make("span", { className: "specimen-number", text: String(index).padStart(2, "0"), attributes: { "aria-hidden": "true" } }));
      const labels = make("div");
      labels.append(make("p", { className: "micro-label", text: "proposed choice" }), make("p", { className: "disposition-tag", text: `proposal / ${capability.disposition}` }));
      head.append(labels);
      detail.append(head, make("h3", { text: capability.name }), make("p", { className: "capability-purpose", text: capability.purpose }));

      const proposal = make("div", { className: "specimen-field proposal" });
      proposal.append(make("h4", { text: "proposed treatment" }), make("p", { text: capability.proposal }));
      const edge = make("div", { className: "specimen-field" });
      edge.append(make("h4", { text: "confidence / unresolved edge" }), make("p", { text: capability.edge }));
      detail.append(proposal, edge);

      if (capability.tension) {
        const tension = make("div", { className: "specimen-field tension" });
        tension.append(make("h4", { text: "authority tension" }), make("p", { text: capability.tension }));
        detail.append(tension);
      }

      const actions = make("fieldset", { className: "review-actions" });
      actions.append(make("legend", { text: "your provisional pencil mark" }));
      [
        ["agree", "✓ looks right"],
        ["discuss", "? needs talk"],
        ["change", "↺ change course"]
      ].forEach(([value, label]) => {
        const button = make("button", {
          className: "review-mark",
          text: label,
          attributes: { type: "button", "aria-pressed": mark === value },
          dataset: { reviewMark: value }
        });
        button.addEventListener("click", () => markCapability(value));
        actions.append(button);
      });
      detail.append(actions);
    };

    kinds.forEach((kind) => {
      const total = kind === "all" ? data.capabilities.length : data.capabilities.filter((capability) => capability.kind === kind).length;
      const button = make("button", {
        text: `${kind} · ${total}`,
        attributes: { type: "button", "aria-pressed": kind === activeFilter },
        dataset: { capabilityFilter: kind }
      });
      button.addEventListener("click", () => {
        activeFilter = kind;
        selectAll("[data-capability-filter]", filterBar).forEach((filter) => filter.setAttribute("aria-pressed", String(filter === button)));
        const visible = visibleCapabilities();
        if (!visible.some(({ id }) => id === activeId)) activeId = visible[0].id;
        renderList();
        renderDetail();
      });
      filterBar.append(button);
    });

    nextButton.addEventListener("click", () => {
      const currentIndex = data.capabilities.findIndex(({ id }) => id === activeId);
      const ordered = [...data.capabilities.slice(currentIndex + 1), ...data.capabilities.slice(0, currentIndex + 1)];
      const next = ordered.find(({ id }) => !reviewMarks.has(id));
      if (!next) {
        status.textContent = "every capability has a pencil mark. the sorting slip is ready.";
        return;
      }
      if (activeFilter !== "all" && next.kind !== activeFilter) {
        activeFilter = "all";
        selectAll("[data-capability-filter]", filterBar).forEach((filter) => filter.setAttribute("aria-pressed", String(filter.dataset.capabilityFilter === "all")));
        renderList();
      }
      activeId = next.id;
      renderList();
      renderDetail();
      detail.setAttribute("tabindex", "-1");
      detail.focus();
      detail.scrollIntoView({ block: "center", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    });

    copyButton.addEventListener("click", async () => {
      try {
        await copyText(buildReviewSlip(reviewMarks));
        status.textContent = "sorting slip copied. paste it into the review conversation before refreshing.";
      } catch {
        status.textContent = "the browser refused clipboard access. pencil marks remain until refresh.";
      }
    });

    renderList();
    renderDetail();
    updateProgress();
  };

  const renderRoadmap = () => {
    if (data.phases.length === 0) {
      select("[data-density-switch]").hidden = true;
      return;
    }
    show("[data-roadmap-section]");
    const list = select("[data-phase-list]");
    const detail = select("[data-phase-detail]");
    const chain = select("[data-causal-chain]");
    let activeId = data.phases[0].id;

    const renderDetail = () => {
      const phase = data.phases.find(({ id }) => id === activeId);
      detail.replaceChildren();
      detail.append(
        make("span", { className: "detail-number", text: `phase ${phase.number}` }),
        make("h3", { text: phase.title }),
        make("p", { className: "detail-status", text: phase.status }),
        make("p", { className: "detail-outcome", text: phase.outcome })
      );
      if (phase.dependencies.length) detail.append(detailBlock("depends on", { items: phase.dependencies }));
      detail.append(
        detailBlock("what belongs here", { items: phase.work }),
        detailBlock("exit gate", { text: phase.exit, className: "exit-gate" }),
        detailBlock("do not smuggle", { text: phase.guard, className: "guard" })
      );
    };

    data.phases.forEach((phase) => {
      const button = make("button", {
        className: "phase-node",
        attributes: { type: "button", "aria-pressed": phase.id === activeId },
        dataset: { phase: phase.id, distance: phase.distance }
      });
      button.append(make("span", { className: "phase-index", text: phase.number, attributes: { "aria-hidden": "true" } }));
      const copy = make("span", { className: "phase-copy" });
      copy.append(make("strong", { text: phase.title }), make("small", { text: phase.short }));
      button.append(copy);
      button.addEventListener("click", () => {
        activeId = phase.id;
        selectAll("[data-phase]", list).forEach((node) => node.setAttribute("aria-pressed", String(node.dataset.phase === activeId)));
        renderDetail();
      });
      list.append(button);
    });

    data.phases.forEach((phase, index) => {
      const step = make("div", { className: "chain-step" });
      step.append(make("strong", { text: phase.title }), make("small", { text: phase.exit }));
      chain.append(step);
      if (index < data.phases.length - 1) chain.append(make("span", { className: "chain-arrow", text: "→", attributes: { "aria-hidden": "true" } }));
    });

    const densityControls = selectAll("button[data-density]");
    densityControls.forEach((button) => {
      button.addEventListener("click", () => {
        document.body.dataset.density = button.dataset.density;
        densityControls.forEach((control) => control.setAttribute("aria-pressed", String(control === button)));
      });
    });
    renderDetail();
  };

  const renderDeployments = () => {
    if (data.deployments.length === 0) return;
    show("[data-deployment-section]");
    const rail = select("[data-deployment-rail]");
    const detail = select("[data-deployment-detail]");
    let activeId = data.deployments[0].id;

    const renderDetail = () => {
      const deployment = data.deployments.find(({ id }) => id === activeId);
      detail.replaceChildren(
        make("p", { className: "micro-label", text: `${deployment.id} gate` }),
        make("h3", { text: deployment.title }),
        make("p", { className: "gate-state", text: deployment.state }),
        make("p", { text: deployment.copy })
      );
      const list = make("ul");
      deployment.gates.forEach((gate) => list.append(make("li", { text: gate })));
      detail.append(list);
    };

    data.deployments.forEach((deployment) => {
      const button = make("button", {
        className: "deployment-node",
        attributes: { type: "button", "aria-pressed": deployment.id === activeId },
        dataset: { deployment: deployment.id }
      });
      button.append(make("strong", { text: deployment.id.toUpperCase() }), make("span", { text: deployment.title }));
      button.addEventListener("click", () => {
        activeId = deployment.id;
        selectAll("[data-deployment]", rail).forEach((node) => node.setAttribute("aria-pressed", String(node.dataset.deployment === activeId)));
        renderDetail();
      });
      rail.append(button);
    });
    renderDetail();
  };

  const renderLanes = () => {
    if (data.lanes.length === 0) return;
    show("[data-lanes-section]");
    const grid = select("[data-lanes]");
    data.lanes.forEach((lane) => {
      const card = make("article", { className: "lane", dataset: { tone: lane.tone } });
      card.append(
        make("span", { className: "lane-status", text: lane.status }),
        make("h3", { text: lane.title }),
        make("p", { text: lane.copy }),
        make("small", { text: lane.note })
      );
      grid.append(card);
    });
  };

  const initialize = () => {
    if (!data || !data.artifact) throw new Error("review-data.js did not provide a valid attention aperture payload");
    document.title = `${data.artifact.title} — attention aperture`;
    appendText("[data-title]", data.artifact.title);
    appendText("[data-eyebrow]", data.artifact.eyebrow);
    appendText("[data-intro]", data.artifact.intro);
    appendText("[data-canonical-sources]", data.artifact.canonicalSources.join(" · "));

    if (data.artifact.next) {
      appendText("[data-next-number]", data.artifact.next.number);
      appendText("[data-next-label]", data.artifact.next.label);
      appendText("[data-next-title]", data.artifact.next.title);
      appendText("[data-next-copy]", data.artifact.next.copy);
    } else select("[data-next-bite]").hidden = true;

    const currentTarget = data.capabilities.length ? "#current-review" : "#roadmap";
    select("[data-next-bite] a")?.setAttribute("href", currentTarget);
    select(".skip-link").setAttribute("href", currentTarget);

    renderFoundations();
    renderCapabilities();
    renderRoadmap();
    renderDeployments();
    renderLanes();
  };

  try {
    initialize();
  } catch (error) {
    show("[data-error]");
    appendText("[data-error-copy]", error.message);
    console.error(error);
  }
})();
