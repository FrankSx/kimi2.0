/*
Copyright 2014 Mozilla Foundation

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

var VIEWER_URL = chrome.runtime.getURL("content/web/viewer.html");

function getViewerURL(pdf_url) {
  return VIEWER_URL + "?file=" + encodeURIComponent(pdf_url);
}

document.addEventListener("animationstart", onAnimationStart, true);
if (document.contentType === "application/pdf") {
  chrome.runtime.sendMessage({ action: "canRequestBody" }, maybeRenderPdfDoc);
}

function onAnimationStart(event) {
  if (event.animationName === "pdfjs-detected-object-or-embed") {
    watchObjectOrEmbed(event.target);
  }
}

// Called for every <object> or <embed> element in the page.
// This may change the type, src/data attributes and/or the child nodes of the
// element. This function only affects elements for the first call. Subsequent
// invocations have no effect.
function watchObjectOrEmbed(elem) {
  var mimeType = elem.type;
  if (mimeType && mimeType.toLowerCase() !== "application/pdf") {
    return;
  }
  // <embed src> <object data>
  var srcAttribute = "src" in elem ? "src" : "data";
  var path = elem[srcAttribute];
  if (!mimeType && !/\.pdf($|[?#])/i.test(path)) {
    return;
  }

  if (
    elem.tagName === "EMBED" &&
    elem.name === "plugin" &&
    elem.parentNode === document.body &&
    elem.parentNode.childElementCount === 1 &&
    elem.src === location.href
  ) {
    return;
  }
  if (elem.tagName === "EMBED" && elem.src === "about:blank") {
    return;
  }

  if (elem.__I_saw_this_element) {
    return;
  }
  elem.__I_saw_this_element = true;

  var tagName = elem.tagName.toUpperCase();
  var updateEmbedOrObject = async () => {
    if (tagName === "EMBED") {
      await replaceEmbedElement(elem);
    } else if (tagName === "OBJECT") {
      await replaceObjectElement(elem);
    }
  };
  updateEmbedOrObject();
}

async function replaceEmbedElement(elem) {
  elem.type = "text/html";
  elem.src = getViewerURL(elem.src);
}

async function replaceObjectElement(elem) {
  var viewerURL = getViewerURL(elem.data);
  var fragment = createReplacementFragment(viewerURL, "100%", "100%");
  elem.parentNode.replaceChild(fragment, elem);
}

function createReplacementFragment(src, width, height) {
  var iframe = document.createElement("iframe");
  iframe.src = src;
  iframe.width = width;
  iframe.height = height;
  iframe.style.border = "none";
  return iframe;
}

function maybeRenderPdfDoc(canRequestBody) {
  if (canRequestBody) {
    renderPdfDoc();
  } else {
    console.log("Not rendering PDF: POST request detected");
  }
}

function renderPdfDoc() {
  var viewerURL = getViewerURL(location.href);
  document.body.textContent = "";
  var iframe = document.createElement("iframe");
  iframe.src = viewerURL;
  iframe.style.width = "100%";
  iframe.style.height = "100%";
  iframe.style.border = "none";
  iframe.style.position = "fixed";
  iframe.style.top = "0";
  iframe.style.left = "0";
  document.body.appendChild(iframe);
}
