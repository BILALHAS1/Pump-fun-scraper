(function () {
  const config = window.DASHBOARD_CONFIG || { autoRefreshSeconds: 1 };
  
  const refreshIntervalLabel = document.getElementById("refresh-interval");
  const lastUpdatedLabel = document.getElementById("last-updated");
  const loadingDiv = document.getElementById("loading");
  const noDataDiv = document.getElementById("no-data");
  const coinsTable = document.getElementById("coins-table");
  const coinsTbody = document.getElementById("coins-tbody");
  const connectionStatus = document.getElementById("connection-status");
  const connectionText = document.getElementById("connection-text");
  
  let eventSource = null;
  let previousPrices = {};
  let newCoinIds = new Set();

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
  
  function setConnectionStatus(status, text) {
    connectionStatus.className = `connection-status ${status}`;
    connectionText.textContent = text;
  }
  
  function getCoinId(token) {
    return token.mint_address || token.symbol || token.name || Math.random().toString();
  }
  
  function getPriceChange(currentPrice, coinId) {
    if (!previousPrices[coinId]) {
      return null;
    }
    const prevPrice = previousPrices[coinId];
    if (prevPrice === currentPrice) {
      return null;
    }
    return currentPrice > prevPrice ? "up" : "down";
  }

  function updateDisplay(data) {
    if (!data || !data.tokens || !Array.isArray(data.tokens)) {
      showNoData();
      return;
    }

    const tokens = data.tokens;
    const newCoins = data.new_coins || [];
    
    if (tokens.length === 0) {
      showNoData();
      return;
    }
    
    // Track new coin IDs
    newCoins.forEach(coin => {
      const coinId = getCoinId(coin);
      newCoinIds.add(coinId);
      // Remove from new coins after 30 seconds
      setTimeout(() => newCoinIds.delete(coinId), 30000);
    });

    const rows = tokens.map((token) => {
      const coinId = getCoinId(token);
      const symbol = token.symbol || "—";
      const name = token.name || "Unknown";
      const currentPrice = token.price || 0;
      const price = formatCurrency(currentPrice, 8);
      const marketCap = formatMarketCap(token.market_cap);
      
      const isNew = newCoinIds.has(coinId);
      const priceChange = getPriceChange(currentPrice, coinId);
      
      // Update previous price
      previousPrices[coinId] = currentPrice;
      
      let priceChangeIndicator = '';
      if (priceChange === 'up') {
        priceChangeIndicator = '<span class="price-change price-up">▲</span>';
      } else if (priceChange === 'down') {
        priceChangeIndicator = '<span class="price-change price-down">▼</span>';
      }
      
      const newBadge = isNew ? '<span class="new-coin-badge">NEW</span>' : '';
      const rowClass = isNew ? 'new-coin-row' : '';

      return `
        <tr class="${rowClass}">
          <td>
            <div class="ticker-name">${symbol}${newBadge}</div>
            <div class="coin-symbol">${name}</div>
          </td>
          <td class="price">${price}${priceChangeIndicator}</td>
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
  
  function connectSSE() {
    if (eventSource) {
      eventSource.close();
    }
    
    setConnectionStatus("connecting", "Connecting...");
    
    eventSource = new EventSource("/api/stream");
    
    eventSource.onopen = function() {
      console.log("SSE connection established");
      setConnectionStatus("connected", "Live");
    };
    
    eventSource.onmessage = function(event) {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "connected") {
          console.log("Connected:", data.message);
          setConnectionStatus("connected", "Live");
        } else if (data.type === "update") {
          updateDisplay(data);
        } else if (data.type === "error") {
          console.error("Server error:", data.message);
        }
      } catch (error) {
        console.error("Error parsing SSE data:", error);
      }
    };
    
    eventSource.onerror = function(error) {
      console.error("SSE connection error:", error);
      setConnectionStatus("disconnected", "Disconnected");
      
      // Try to reconnect after 5 seconds
      setTimeout(() => {
        console.log("Attempting to reconnect...");
        connectSSE();
      }, 5000);
    };
  }

  function init() {
    const intervalText = formatRefreshInterval(config.autoRefreshSeconds);
    refreshIntervalLabel.textContent = intervalText;
    
    // Use SSE for real-time updates
    connectSSE();
    
    // Fallback: also fetch data initially in case SSE takes time to connect
    fetchData();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  
  // Clean up on page unload
  window.addEventListener("beforeunload", function() {
    if (eventSource) {
      eventSource.close();
    }
  });
})();
