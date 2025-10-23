(function () {
  const config = window.DASHBOARD_CONFIG || { autoRefreshSeconds: 300 };
  
  const refreshIntervalLabel = document.getElementById("refresh-interval");
  const lastUpdatedLabel = document.getElementById("last-updated");
  const loadingDiv = document.getElementById("loading");
  const noDataDiv = document.getElementById("no-data");
  const coinsTable = document.getElementById("coins-table");
  const coinsTbody = document.getElementById("coins-tbody");

  function formatCurrency(value, decimals = 6) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    const num = Number(value);
    if (num === 0) return "$0.00";
    
    if (num < 0.000001) {
      return `$${num.toExponential(2)}`;
    }
    
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: decimals,
    }).format(num);
  }

  function formatMarketCap(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "—";
    }
    const num = Number(value);
    if (num === 0) return "$0";
    
    if (num >= 1000000) {
      return `$${(num / 1000000).toFixed(2)}M`;
    } else if (num >= 1000) {
      return `$${(num / 1000).toFixed(2)}K`;
    } else {
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      }).format(num);
    }
  }

  function formatTimestamp() {
    const now = new Date();
    const options = {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    };
    return now.toLocaleString("en-US", options);
  }

  function formatRefreshInterval(seconds) {
    if (seconds >= 60) {
      const minutes = Math.floor(seconds / 60);
      return `${minutes} minute${minutes !== 1 ? "s" : ""}`;
    }
    return `${seconds} second${seconds !== 1 ? "s" : ""}`;
  }

  function updateDisplay(data) {
    if (!data || !data.tokens || !Array.isArray(data.tokens)) {
      showNoData();
      return;
    }

    const tokens = data.tokens;
    
    if (tokens.length === 0) {
      showNoData();
      return;
    }

    const rows = tokens.map((token) => {
      const symbol = token.symbol || "—";
      const name = token.name || "Unknown";
      const price = formatCurrency(token.price, 8);
      const marketCap = formatMarketCap(token.market_cap);

      return `
        <tr>
          <td>
            <div class="ticker-name">${symbol}</div>
            <div class="coin-symbol">${name}</div>
          </td>
          <td class="price">${price}</td>
          <td class="market-cap">${marketCap}</td>
        </tr>
      `;
    });

    coinsTbody.innerHTML = rows.join("");
    
    loadingDiv.style.display = "none";
    noDataDiv.style.display = "none";
    coinsTable.style.display = "table";

    const timestamp = formatTimestamp();
    lastUpdatedLabel.textContent = `Last updated: ${timestamp}`;
  }

  function showNoData() {
    loadingDiv.style.display = "none";
    coinsTable.style.display = "none";
    noDataDiv.style.display = "block";
    
    const timestamp = formatTimestamp();
    lastUpdatedLabel.textContent = `Last updated: ${timestamp}`;
  }

  function showLoading() {
    loadingDiv.style.display = "block";
    noDataDiv.style.display = "none";
    coinsTable.style.display = "none";
  }

  async function fetchData() {
    try {
      const response = await fetch("/api/data");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      updateDisplay(data);
    } catch (error) {
      console.error("Error fetching data:", error);
      showNoData();
    }
  }

  function init() {
    const intervalText = formatRefreshInterval(config.autoRefreshSeconds);
    refreshIntervalLabel.textContent = intervalText;
    
    fetchData();
    
    setInterval(fetchData, config.autoRefreshSeconds * 1000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
