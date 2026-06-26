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

// Suppress Chrome's built-in PDF viewer to avoid conflicts with this extension.
// This module handles the suppression logic to ensure PDF.js takes precedence.

(function SuppressUpdateClosure() {
  // Check if the built-in viewer should be suppressed
  async function checkAndSuppressBuiltInViewer() {
    try {
      // Check if suppression is already applied
      const result = await chrome.storage.local.get("builtinViewerSuppressed");
      if (result.builtinViewerSuppressed) {
        return;
      }

      // Attempt to suppress the built-in PDF viewer
      // Note: In Manifest V3, direct suppression of built-in features
      // is limited. This serves as a marker for the extension's intent.
      await chrome.storage.local.set({ builtinViewerSuppressed: true });
      console.log("PDF.js: Built-in viewer suppression marker set.");
    } catch (error) {
      console.error("PDF.js: Failed to set suppression marker:", error);
    }
  }

  // Run on startup
  checkAndSuppressBuiltInViewer();
})();
