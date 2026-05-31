let ws = null;
let reconnectTimer = null;

function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  ws = new WebSocket("ws://localhost:9223");

  ws.onopen = () => {
    console.log("[browser-to-cli] Connected to CLI");
  };

  ws.onclose = () => {
    console.log("[browser-to-cli] Disconnected, retrying in 2s...");
    ws = null;
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 2000);
  };

  ws.onerror = () => {
    ws?.close();
  };
}

// Relay messages from content scripts to the WebSocket
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "BROWSER_TO_CLI") {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message.payload));
    }
    sendResponse({ ok: true });
    return true;
  }
});

// Keep service worker alive via periodic ping
setInterval(() => {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  } else {
    connect();
  }
}, 10000);

connect();
