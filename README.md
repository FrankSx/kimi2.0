# Kimi 2.0 System Files

This repository contains the system files for Kimi 2.0, including browser automation, Jupyter kernel management, and PDF viewer extension.

## Structure

```
.
├── browser_guard.py          # Browser automation guard using Playwright
├── jupyter_kernel.py         # Jupyter kernel management
├── kernel_server.py          # FastAPI server for kernel management
├── utils.py                  # Utility functions
├── pdf-viewer/               # Chrome PDF Viewer extension (Mozilla PDF.js)
│   ├── manifest.json
│   ├── background.js
│   ├── preserve-referer.js
│   ├── contentscript.js
│   ├── pdfHandler.js
│   ├── extension-router.js
│   ├── telemetry.js
│   ├── suppress-update.js
│   ├── contentstyle.css
│   ├── preferences_schema.json
│   ├── LICENSE
│   ├── options/
│   │   ├── migration.js
│   │   ├── options.html
│   │   └── options.js
│   └── content/web/viewer.html
└── logs/
    └── chromium.log
```

## Components

### Browser Guard (`browser_guard.py`)
- Automated browser management using Playwright
- Two modes: `BrowserGuard` (Playwright-based) and `BrowserCDPGuard` (CDP-based)
- Automatic tab monitoring and window management
- Chromium profile persistence
- PDF viewer extension loading

### Jupyter Kernel (`jupyter_kernel.py`)
- Jupyter kernel lifecycle management
- Code execution with timeout handling
- Automatic kernel health monitoring and restart
- Matplotlib initialization with CJK font support

### Kernel Server (`kernel_server.py`)
- FastAPI-based REST API for kernel management
- Endpoints:
  - `GET /` - Service info
  - `GET /health` - Health check
  - `POST /kernel/reset` - Reset kernel
  - `POST /kernel/interrupt` - Interrupt kernel execution
  - `GET /kernel/connection` - Get connection info
  - `GET /kernel/status` - Get kernel status

### Utils (`utils.py`)
- Screen size detection via `xrandr`
- Shell command execution helpers

### PDF Viewer Extension
- Mozilla PDF.js Chrome extension
- Handles PDF rendering in the browser
- Supports various PDF sources (http, https, file, blob, data URIs)
- Customizable viewer preferences

## License

The PDF viewer extension is licensed under the Apache License 2.0 (Mozilla Foundation).
The Python source files are proprietary to Kimi 2.0.
