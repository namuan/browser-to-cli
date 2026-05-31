(function () {
  function resolveUrl(raw) {
    try { return new URL(raw, window.location.href).href; } catch (_) { return raw; }
  }

  function send(payload) {
    window.postMessage({ type: "BROWSER_TO_CLI", payload }, "*");
  }

  function isTextType(ct) {
    return /text|json|javascript|xml|form-urlencoded/i.test(ct);
  }

  function parseHeaders(raw) {
    const h = {};
    raw.trim().split(/[\r\n]+/).forEach(line => {
      const i = line.indexOf(": ");
      if (i > 0) h[line.slice(0, i)] = line.slice(i + 2);
    });
    return h;
  }

  // ── fetch interception ──────────────────────────────────────────────

  const origFetch = window.fetch;
  window.fetch = async function (resource, init) {
    const method = (init?.method || "GET").toUpperCase();
    const url = resolveUrl(typeof resource === "string" ? resource : resource.url);
    const reqHeaders = {};
    if (init?.headers) {
      if (init.headers instanceof Headers) {
        init.headers.forEach((v, k) => (reqHeaders[k] = v));
      } else if (Array.isArray(init.headers)) {
        init.headers.forEach(([k, v]) => (reqHeaders[k] = v));
      } else {
        Object.assign(reqHeaders, init.headers);
      }
    }

    const requestData = {
      method,
      url,
      page_url: window.location.href,
      headers: reqHeaders,
      body: init?.body ?? null,
      resource_type: "fetch",
      timestamp: new Date().toISOString(),
    };

    let response;
    try {
      response = await origFetch.call(this, resource, init);
    } catch (err) {
      send({ type: "request", ...requestData, response: { status: 0 } });
      throw err;
    }

    const clone = response.clone();
    captureResponse(clone).then(respData => {
      send({ type: "request", ...requestData, response: respData });
    });

    return response;
  };

  async function captureResponse(response) {
    const headers = {};
    response.headers.forEach((v, k) => (headers[k] = v));

    let body = null;
    if (isTextType(response.headers.get("content-type") || "")) {
      try { body = await response.text(); } catch (_) {}
    }

    return { status: response.status, headers, body };
  }

  // ── XMLHttpRequest interception ─────────────────────────────────────

  const OrigXHR = window.XMLHttpRequest;

  window.XMLHttpRequest = function () {
    const xhr = new OrigXHR();
    let reqMethod = "GET", reqUrl = "";
    const reqHeaders = {};
    let reqBody = null;

    const origOpen = xhr.open;
    xhr.open = function (method, url) {
      reqMethod = method.toUpperCase();
      reqUrl = resolveUrl(url);
      return origOpen.apply(this, arguments);
    };

    const origSetRequestHeader = xhr.setRequestHeader;
    xhr.setRequestHeader = function (name, value) {
      reqHeaders[name] = value;
      return origSetRequestHeader.apply(this, arguments);
    };

    const origSend = xhr.send;
    xhr.send = function (body) {
      reqBody = body;

      const requestData = {
        method: reqMethod,
        url: reqUrl,
        page_url: window.location.href,
        headers: { ...reqHeaders },
        body: reqBody,
        resource_type: "xhr",
        timestamp: new Date().toISOString(),
      };

      xhr.addEventListener("loadend", () => {
        const respHeaders = parseHeaders(xhr.getAllResponseHeaders() || "");
        let respBody = null;
        if (isTextType(respHeaders["content-type"] || "")) {
          try { respBody = xhr.responseText; } catch (_) {}
        }

        send({
          type: "request",
          ...requestData,
          response: { status: xhr.status, headers: respHeaders, body: respBody },
        });
      });

      return origSend.apply(this, arguments);
    };

    return xhr;
  };
})();
