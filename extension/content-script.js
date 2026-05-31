(function () {
  window.addEventListener("message", (event) => {
    if (event.source !== window) return;
    if (event.data?.type !== "BROWSER_TO_CLI") return;

    chrome.runtime.sendMessage({
      type: "BROWSER_TO_CLI",
      payload: event.data.payload,
    });
  });
})();
