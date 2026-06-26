/*
Copyright 2024 Mozilla Foundation

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

"use strict";

// Telemetry module for PDF.js Chrome extension
// Collects anonymous usage statistics to help improve the extension.

(function TelemetryClosure() {
  const TELEMETRY_URL = "https://telemetry.pdf.js/";
  const STORAGE_KEY = "telemetry_last_report";
  const REPORT_INTERVAL_MS = 7 * 24 * 60 * 60 * 1000; // 1 week

  async function shouldReport() {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEY);
      const lastReport = result[STORAGE_KEY];
      if (!lastReport) {
        return true;
      }
      return Date.now() - lastReport >= REPORT_INTERVAL_MS;
    } catch {
      return false;
    }
  }

  async function markReported() {
    try {
      await chrome.storage.local.set({ [STORAGE_KEY]: Date.now() });
    } catch {
      // Ignore storage errors
    }
  }

  async function isTelemetryDisabled() {
    try {
      const result = await chrome.storage.sync.get("disableTelemetry");
      return result.disableTelemetry === true;
    } catch {
      return false;
    }
  }

  async function reportTelemetry() {
    if (await isTelemetryDisabled()) {
      return;
    }
    if (!(await shouldReport())) {
      return;
    }

    try {
      const manifest = chrome.runtime.getManifest();
      const data = {
        version: manifest.version,
        minimum_chrome_version: manifest.minimum_chrome_version,
        user_agent: navigator.userAgent,
      };

      // Send telemetry data (fire and forget)
      fetch(TELEMETRY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        keepalive: true,
      }).catch(() => {
        // Silently ignore network errors
      });

      await markReported();
    } catch {
      // Silently ignore any errors
    }
  }

  // Report telemetry on extension startup
  reportTelemetry();
})();
