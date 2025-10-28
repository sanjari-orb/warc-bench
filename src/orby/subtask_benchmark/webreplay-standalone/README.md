# Webreplay Standalone

This is a standalone version of the Orby Webreplay package that focuses on the "serve" command to replay WARC files. This code is directly copied from the original Orby webreplay implementation to maintain full compatibility.

## Installation

1. cd into webreplay-standalone
```bash
cd webreplay-standalone
```

2. Install dependencies:

```bash
npm install
```

3. Build the project:

```bash
npm run build
```

## Usage

### Replaying a WARC File

To replay a WARC file, run:

```
node dist/index.js serve ../environments/web_archives/<archive>.wacz  <start_url>  --port 3000   --debugging-port 9222
```
You can add the [--headless] flag to open the playwright instance in headless mode.

After running the command, the browser should be accessible using

```
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Connect to the existing browser instance through CDP
    debugging_port = 9222
    browser_url = f"http://localhost:{debugging_port}"
    browser = p.chromium.connect_over_cdp(browser_url)
```
