(function () {
  const { DateTime } = luxon;
  const config = window.DASHBOARD_CONFIG || { autoRefreshSeconds: 30 };

  const refreshIntervalLabel = document.getElementById("refresh-interval");
  const lastUpdatedLabel = document.getElementById("last-updated");
  const dataSourceLabel = document.getElementById("data-source");
  const launchesList = document.getElementById("launches-list");

  const tokenSearchInput = document.getElementById("tokenSearch");
  const tokenSortSelect = document.getElementById("tokenSort");
  const tokenTableBody = document.querySelector("#tokensTable tbody");

  const transactionFilterSelect = document.getElementById(
    "transactionActionFilter"
  );
  const transactionTableBody = document.querySelector(
    "#transactionsTable tbody"
  );

  let priceTrendChart = null;
  let volumeChart = null;
  let activityChart = null;

  const tokenState = {
    data: [],
    filtered: [],
    sortKey: "market_cap",
    sortOrder: "desc",
  };

  const transactionState = {
    data: [],
    filtered: [],
    action: "all",
  };

  function formatCurrency(value, digits = 2) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    return new Intl.NumberFormat("en", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: digits,
      minimumFractionDigits: digits,
    }).format(Number(value));
  }

  function formatCompactCurrency(value) {
    if (value === null || value === undefined) {
      return "—";
    }
    return new Intl.NumberFormat("en", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(Number(value));
  }

  function formatNumber(value, digits = 2) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    return new Intl.NumberFormat("en", {
      maximumFractionDigits: digits,
    }).format(Number(value));
  }

  function formatDateTime(isoString) {
    if (!isoString) return "—";
    const dt = DateTime.fromISO(isoString, { zone: "utc" });
    if (!dt.isValid) return "—";
    return dt.toFormat("MMM dd, yyyy HH:mm 'UTC'");
  }

  function formatRelativeTime(isoString) {
    if (!isoString) return "—";
    const dt = DateTime.fromISO(isoString, { zone: "utc" });
    if (!dt.isValid) return "—";
    const relative = dt.toRelative();
    return relative || dt.toFormat("MMM dd, yyyy HH:mm");
  }

  function maskedAddress(address) {
    if (!address) return "—";
    if (address.length <= 10) return address;
    return `${address.slice(0, 4)}…${address.slice(-4)}`;
  }

  function ensureAbsoluteUrl(value) {
    if (!value) return null;
    const trimmed = value.trim();
    if (!trimmed) return null;
    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed;
    }
    return `https://${trimmed}`;
  }

  function resolveTwitterUrl(value) {
    if (!value) return null;
    const trimmed = value.trim();
    if (!trimmed) return null;
    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed;
    }
    const handle = trimmed.replace(/^@/, "");
    if (!handle) return null;
    return `https://twitter.com/${handle}`;
  }

  function resolveTelegramUrl(value) {
    if (!value) return null;
    const trimmed = value.trim();
    if (!trimmed) return null;
    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed;
    }
    if (trimmed.startsWith("@")) {
      return `https://t.me/${trimmed.slice(1)}`;
    }
    return `https://${trimmed}`;
  }

  function updateSummary(summary, dataset) {
    const totalTokensEl = document.getElementById("summary-total-tokens");
    const totalVolumeEl = document.getElementById("summary-24h-volume");
    const totalTransactionsEl = document.getElementById(
      "summary-total-transactions"
    );
    const topTokenEl = document.getElementById("summary-top-token");
    const topTokenMarketCapEl = document.getElementById(
      "summary-top-token-market-cap"
    );

    totalTokensEl.textContent = summary.total_tokens ?? "0";
    totalVolumeEl.textContent = formatCompactCurrency(summary.total_volume_24h);
    totalTransactionsEl.textContent = summary.total_transactions ?? "0";

    if (summary.top_token && summary.top_token.name) {
      const { name, symbol, market_cap, price } = summary.top_token;
      topTokenEl.textContent = symbol ? `${symbol}` : name;
      const details = [];
      if (name) details.push(name);
      if (price !== null && price !== undefined) {
        details.push(`Price: ${formatCurrency(price)}`);
      }
      if (market_cap !== null && market_cap !== undefined) {
        details.push(`MCap: ${formatCompactCurrency(market_cap)}`);
      }
      topTokenMarketCapEl.textContent = details.join(" · ");
    } else {
      topTokenEl.textContent = "—";
      topTokenMarketCapEl.textContent = "";
    }

    const generated = dataset.generated_at;
    const datasetTs =
      summary.latest_activity || dataset.dataset_timestamp || dataset.scrape_timestamp;

    if (generated) {
      lastUpdatedLabel.textContent = `Last refreshed ${formatRelativeTime(
        generated
      )} (${formatDateTime(generated)})`;
    } else {
      lastUpdatedLabel.textContent = "Last refreshed —";
    }

    const sourcePath = dataset.source_path || "sample_output.json";
    const usingSample = Boolean(dataset.using_sample_data);
    dataSourceLabel.textContent = `Loaded from ${sourcePath}${
      usingSample ? " (sample dataset)" : ""
    }`;

    if (datasetTs) {
      const latestActivityEl = document.createElement("span");
      latestActivityEl.className = "ms-2 badge bg-secondary bg-opacity-75";
      latestActivityEl.textContent = `Latest activity ${formatRelativeTime(
        datasetTs
      )}`;
      lastUpdatedLabel.appendChild(latestActivityEl);
    }
  }

  function updateTokens(tokens) {
    tokenState.data = Array.isArray(tokens) ? tokens.slice() : [];
    applyTokenFilters();
  }

  function applyTokenFilters() {
    const searchValue = (tokenSearchInput.value || "").trim().toLowerCase();
    tokenState.filtered = tokenState.data.filter((token) => {
      if (!searchValue) return true;
      const haystack = [
        token.name,
        token.symbol,
        token.mint_address,
        token.description,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(searchValue);
    });

    sortTokens();
    renderTokens();
  }

  function sortTokens() {
    const key = tokenState.sortKey;
    const direction = tokenState.sortOrder === "desc" ? -1 : 1;

    const getComparableValue = (token) => {
      if (key === "created_timestamp") {
        const ts =
          token.created_timestamp || token.scraped_at || token.launched_at;
        const dt = Date.parse(ts || "1970-01-01T00:00:00Z");
        return Number.isNaN(dt) ? 0 : dt;
      }
      return Number(token[key]) || 0;
    };

    tokenState.filtered.sort((a, b) => {
      const aVal = getComparableValue(a);
      const bVal = getComparableValue(b);
      if (aVal === bVal) return 0;
      return aVal > bVal ? direction : -direction;
    });
  }

  function renderTokens() {
    const rows = tokenState.filtered.map((token) => {
      const symbol = token.symbol || "—";
      const name = token.name || "Unknown";
      const price = formatCurrency(token.price, 6);
      const marketCap = formatCompactCurrency(token.market_cap);
      const volume = formatCompactCurrency(token.volume_24h);
      const timestamp =
        token.created_timestamp || token.scraped_at || token.launched_at;
      const relativeTime = formatRelativeTime(timestamp);
      const absoluteTime = formatDateTime(timestamp);

      return `
        <tr>
          <td>
            <div class="fw-semibold">${symbol}</div>
            <div class="text-muted small">${name}</div>
          </td>
          <td>${price}</td>
          <td>${marketCap}</td>
          <td>${volume}</td>
          <td>
            <span class="d-block">${relativeTime}</span>
            <span class="text-muted small">${absoluteTime}</span>
          </td>
        </tr>
      `;
    });
    tokenTableBody.innerHTML = rows.join("");
  }

  function updateTransactions(transactions) {
    transactionState.data = Array.isArray(transactions) ? transactions.slice() : [];
    applyTransactionFilters();
  }

  function applyTransactionFilters() {
    const filter = transactionState.action;
    transactionState.filtered = transactionState.data.filter((tx) => {
      if (filter === "all") return true;
      return String(tx.action || "").toLowerCase() === filter;
    });
    renderTransactions();
  }

  function renderTransactions() {
    const rows = transactionState.filtered
      .sort((a, b) => {
        const aTime = Date.parse(a.timestamp || a.scraped_at || 0);
        const bTime = Date.parse(b.timestamp || b.scraped_at || 0);
        return bTime - aTime;
      })
      .map((tx) => {
        const action = String(tx.action || "?").toLowerCase();
        const tokenLabel = tx.symbol || tx.token_symbol || maskedAddress(tx.token_mint);
        const amount = formatNumber(tx.amount);
        const price = formatCurrency(tx.price, 6);
        const value = formatCurrency((Number(tx.amount) || 0) * (Number(tx.price) || 0));
        const user = maskedAddress(tx.user);
        const timestamp = tx.timestamp || tx.scraped_at;
        const relative = formatRelativeTime(timestamp);
        const absolute = formatDateTime(timestamp);

        return `
        <tr>
          <td>
            <div class="fw-semibold">${tokenLabel || "—"}</div>
            <div class="text-muted small">${maskedAddress(tx.token_mint)}</div>
          </td>
          <td>
            <span class="badge action-${action}">${action.toUpperCase()}</span>
          </td>
          <td>${amount}</td>
          <td>${price}</td>
          <td>${value}</td>
          <td>${user}</td>
          <td>
            <span class="d-block">${relative}</span>
            <span class="text-muted small">${absolute}</span>
          </td>
        </tr>
      `;
      });

    transactionTableBody.innerHTML = rows.join("");
  }

  function updateLaunchesTimeline(launches) {
    if (!Array.isArray(launches) || launches.length === 0) {
      launchesList.innerHTML = "<p class=\"text-muted mb-0\">No recent launches.</p>";
      return;
    }

    const items = launches.map((launch) => {
      const timestamp = launch.timestamp;
      const relative = formatRelativeTime(timestamp);
      const absolute = formatDateTime(timestamp);
      const name = launch.name || launch.symbol || "Unknown";
      const price = formatCurrency(launch.price, 6);
      const volume = formatCompactCurrency(launch.volume_24h);
      const marketCap = formatCompactCurrency(launch.market_cap);
      const linkParts = [];
      const websiteUrl = ensureAbsoluteUrl(launch.website);
      if (websiteUrl) {
        linkParts.push(
          `<a href="${websiteUrl}" target="_blank" rel="noopener noreferrer">Website</a>`
        );
      }
      const twitterUrl = resolveTwitterUrl(launch.twitter);
      if (twitterUrl) {
        linkParts.push(
          `<a href="${twitterUrl}" target="_blank" rel="noopener noreferrer">Twitter</a>`
        );
      }
      const telegramUrl = resolveTelegramUrl(launch.telegram);
      if (telegramUrl) {
        linkParts.push(
          `<a href="${telegramUrl}" target="_blank" rel="noopener noreferrer">Telegram</a>`
        );
      }
      const links = linkParts.join(" · ");

      const linkHtml = links
        ? `<div class="launch-meta mt-1">${links}</div>`
        : "";

      return `
        <div class="launch-item">
          <div class="fw-semibold">${name}</div>
          <div class="launch-meta text-muted">
            ${relative} · ${absolute}
          </div>
          <div class="launch-meta">Price ${price} · MCap ${marketCap} · Vol ${volume}</div>
          <div class="launch-meta text-muted">Mint ${maskedAddress(launch.mint_address)}</div>
          ${linkHtml}
        </div>
      `;
    });

    launchesList.innerHTML = items.join("");
  }

  function updateCharts(charts) {
    if (!charts) return;
    const priceCanvas = document.getElementById("priceTrendChart");
    const volumeCanvas = document.getElementById("volumeChart");
    const activityCanvas = document.getElementById("activityChart");

    const priceData = charts.price_trend || { labels: [], prices: [], market_caps: [] };
    const volumeData = charts.volume_by_token || { labels: [], buy: [], sell: [] };
    const timelineData = charts.transactions_timeline || { labels: [], counts: [] };
    const launchesData = charts.launches_timeline || { labels: [], counts: [] };

    if (priceCanvas) {
      const datasets = [];
      if (priceData.prices.length) {
        datasets.push({
          label: "Price (USD)",
          data: priceData.prices,
          borderColor: "#0d6efd",
          backgroundColor: "rgba(13, 110, 253, 0.2)",
          tension: 0.35,
          yAxisID: "y",
        });
      }
      if (priceData.market_caps.length) {
        datasets.push({
          label: "Market Cap (USD)",
          data: priceData.market_caps,
          borderColor: "#6610f2",
          backgroundColor: "rgba(102, 16, 242, 0.12)",
          tension: 0.3,
          yAxisID: "y1",
        });
      }
      if (priceTrendChart) {
        priceTrendChart.data.labels = priceData.labels;
        priceTrendChart.data.datasets = datasets;
        priceTrendChart.update();
      } else {
        priceTrendChart = new Chart(priceCanvas, {
          type: "line",
          data: {
            labels: priceData.labels,
            datasets,
          },
          options: {
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            stacked: false,
            scales: {
              y: {
                type: "linear",
                position: "left",
                ticks: { callback: (value) => formatNumber(value, 6) },
              },
              y1: {
                type: "linear",
                position: "right",
                grid: { drawOnChartArea: false },
                ticks: {
                  callback: (value) => formatNumber(value),
                },
              },
            },
            plugins: {
              legend: { display: true },
            },
          },
        });
      }
    }

    if (volumeCanvas) {
      if (volumeChart) {
        volumeChart.data.labels = volumeData.labels;
        volumeChart.data.datasets[0].data = volumeData.buy;
        volumeChart.data.datasets[1].data = volumeData.sell;
        volumeChart.update();
      } else {
        volumeChart = new Chart(volumeCanvas, {
          type: "bar",
          data: {
            labels: volumeData.labels,
            datasets: [
              {
                label: "Buy Value",
                data: volumeData.buy,
                backgroundColor: "rgba(25, 135, 84, 0.7)",
              },
              {
                label: "Sell Value",
                data: volumeData.sell,
                backgroundColor: "rgba(220, 53, 69, 0.7)",
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              y: {
                ticks: { callback: (value) => formatNumber(value) },
              },
            },
          },
        });
      }
    }

    if (activityCanvas) {
      const combinedLabels = Array.from(
        new Set([...timelineData.labels, ...launchesData.labels])
      ).sort();

      const txData = combinedLabels.map((label) => {
        const idx = timelineData.labels.indexOf(label);
        return idx >= 0 ? timelineData.counts[idx] : 0;
      });

      const launchData = combinedLabels.map((label) => {
        const idx = launchesData.labels.indexOf(label);
        return idx >= 0 ? launchesData.counts[idx] : 0;
      });

      if (activityChart) {
        activityChart.data.labels = combinedLabels;
        activityChart.data.datasets[0].data = txData;
        activityChart.data.datasets[1].data = launchData;
        activityChart.update();
      } else {
        activityChart = new Chart(activityCanvas, {
          type: "line",
          data: {
            labels: combinedLabels,
            datasets: [
              {
                label: "Transactions",
                data: txData,
                borderColor: "#0d6efd",
                backgroundColor: "rgba(13, 110, 253, 0.15)",
                tension: 0.35,
                fill: true,
              },
              {
                label: "Launches",
                data: launchData,
                borderColor: "#ffc107",
                backgroundColor: "rgba(255, 193, 7, 0.2)",
                tension: 0.35,
                fill: true,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
          },
        });
      }
    }
  }

  async function fetchData() {
    try {
      const response = await fetch("/api/data", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
      }
      const payload = await response.json();
      updateSummary(payload.summary || {}, payload);
      updateTokens(payload.tokens || []);
      updateTransactions(payload.transactions || []);
      updateLaunchesTimeline(payload.launches_timeline || []);
      updateCharts(payload.charts || {});
    } catch (error) {
      console.error("Failed to refresh dashboard data", error);
    }
  }

  function init() {
    const intervalSeconds = Number(config.autoRefreshSeconds) || 30;
    refreshIntervalLabel.textContent = `${intervalSeconds}s`;

    tokenSearchInput.addEventListener("input", applyTokenFilters);
    tokenSortSelect.addEventListener("change", (event) => {
      tokenState.sortKey = event.target.value;
      tokenState.sortOrder = "desc";
      applyTokenFilters();
    });

    tokenSortSelect.dispatchEvent(new Event("change"));

    transactionFilterSelect.addEventListener("change", (event) => {
      transactionState.action = event.target.value;
      applyTransactionFilters();
    });

    fetchData();
    if (intervalSeconds > 0) {
      setInterval(fetchData, intervalSeconds * 1000);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
