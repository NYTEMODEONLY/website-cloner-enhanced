# Website Cloner Enhanced

The Website Cloner Enhanced is a Python script that recursively downloads an entire website, including its HTML, CSS, JavaScript, images, and other media resources. This tool preserves the website's directory structure and is useful for archiving websites or offline browsing.

## Features

- **Complete Website Crawling**: Recursively follows internal links to download all pages.
- **Directory Structure Preservation**: Maintains the original website's directory structure.
- **Comprehensive Resource Download**: 
  - HTML pages
  - CSS stylesheets
  - JavaScript files
  - Images and icons
  - Media files (videos, audio)
  - iFrames and embedded content
- **Link Rewriting**: Updates all internal links to point to the local files.
- **External Resource Handling**: Downloads external resources and stores them in a separate folder.
- **Cycle Detection**: Avoids infinite loops by tracking visited URLs.
- **Rate Limiting**: Configurable delays between requests to be respectful to the target server.
- **Command-Line Interface**: Flexible CLI options for customizing the cloning process.
- **Smart Site Structure Detection**: Automatically detects the website structure type and uses the appropriate cloning strategy.
- **Template-Style Website Support**: Special handling for websites using relative paths (e.g., './assets/') common in HTML templates.
- **Live Progress Display**: Real-time animation and progress tracking in the terminal.
- **Asset Batch Processing**: Efficient downloading of resource groups with progress tracking.
- **Path Normalization**: Robust handling of various path formats including relative and absolute paths.

## How It Works

The script uses two main strategies for website cloning:

### 1. Recursive Crawling (Standard Websites)
For standard websites, it uses a breadth-first search algorithm:

1. It starts with the initial URL and adds it to a processing queue.
2. For each URL in the queue, it:
   - Downloads the HTML content
   - Extracts all resources (CSS, JS, images, etc.)
   - Downloads these resources
   - Updates the HTML to reference local copies
   - Extracts all internal links and adds them to the queue
3. It maintains a set of visited URLs to avoid processing the same page multiple times.
4. The process continues until all reachable pages are downloaded.

### 2. Direct Asset Cloning (Template Websites)
For websites using template-style structure with relative paths (e.g., './assets/'):

1. It identifies and downloads all HTML pages from internal links.
2. It scans all HTML files to find asset references (CSS, JS, images).
3. It directly downloads all assets while preserving the original path structure.
4. This approach ensures that websites using relative paths maintain their structure.

## Setup and Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/NYTEMODEONLY/website-cloner-enhanced.git
   cd website-cloner-enhanced
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the script with command-line arguments:
   ```bash
   python website_cloner.py [URL] -o [OUTPUT_FOLDER] --min-delay [MIN] --max-delay [MAX]
   ```
   
   Example:
   ```bash
   python website_cloner.py https://example.com -o cloned_site --min-delay 2 --max-delay 5
   ```
   
   Command-line options:
   - `[URL]`: The URL of the website to clone (required)
   - `-o, --output`: The output folder (default: "cloned_website")
   - `--min-delay`: Minimum delay between requests in seconds (default: 1.0)
   - `--max-delay`: Maximum delay between requests in seconds (default: 3.0)
   - `--debug`: Enable debug output

## Website Type Support

The cloner automatically detects the website type:

1. **Standard Websites**: Websites with absolute paths or standard relative paths.
2. **Template Websites**: Websites using './assets/' style paths common in HTML templates.

For template websites (often identified by paths like '/HTML/' in the URL or './assets/' in the source), the cloner uses a direct asset cloning approach for better results.

## Progress Display

The tool features a real-time terminal display with:
- Animated spinner showing current status
- Current file being processed
- Download progress bar and statistics
- Rate limiting status
- Error and success counts

## Requirements
- Python 3.7+
- requests
- beautifulsoup4
- rich (for terminal UI)

To install the required packages, you can use the following command:
```bash
pip install requests beautifulsoup4 rich
```

## License
This project is licensed under the MIT License.

---
Forked with ❤️ by [NYTEMODE](https://nytemode.com)
