# Website Cloner Enhanced

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.7%2B-blue" alt="Python 3.7+">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License: MIT">
  <img src="https://img.shields.io/badge/Version-1.2.0-orange" alt="Version 1.2.0">
</p>

A powerful Python tool that creates perfect local copies of websites by downloading all HTML, CSS, JavaScript, images, and media resources while preserving the original directory structure. This enhanced website cloner automatically detects website types and adapts its strategy accordingly.

## 🚀 Features

### Core Capabilities
- **Intelligent Website Detection**: Automatically identifies website structure type and applies the appropriate cloning strategy
- **Complete Website Crawling**: Recursively follows all internal links to download the entire site structure
- **Perfect Directory Preservation**: Maintains the exact original directory structure for flawless local browsing
- **Comprehensive Resource Handling**: Downloads all HTML, CSS, JS, images, videos, fonts, and more
- **Link Rewriting**: Automatically updates all internal links to point to local files

### Advanced Features
- **Smart Template Website Support**: Special handling for template-style websites using relative paths (e.g., './assets/')
- **External Resource Management**: Downloads and organizes external resources in a dedicated folder
- **Cycle Detection**: Avoids infinite loops by tracking visited URLs
- **Rate Limiting**: Configurable delays between requests to respect server limitations
- **Resource Validation**: Verifies downloaded resources for completeness and integrity

### User Experience
- **Interactive Terminal UI**: Live progress display with animations and real-time statistics
- **Flexible Command-Line Interface**: Customizable options for tailoring the cloning process
- **Detailed Logging**: Comprehensive logging system with configurable verbosity levels
- **Error Recovery**: Automatic retry mechanism with exponential backoff for failed downloads

## 📋 How It Works

The enhanced cloner employs two distinct strategies, automatically selecting the most appropriate approach based on website structure:

### 1. Recursive Crawling Strategy
For standard websites with absolute paths:

1. **Initial Page Download**: Begins with the specified URL
2. **Resource Extraction**: Parses HTML to identify CSS, JS, images, and other assets
3. **Link Discovery**: Extracts all internal links to other pages
4. **Breadth-First Crawling**: Processes all pages methodically, downloading resources and following links
5. **Path Normalization**: Handles various path formats including relative and absolute paths

### 2. Template Site Strategy
For template-style websites (typically containing './assets/' or similar patterns):

1. **Template Detection**: Identifies template structure from URL or HTML content patterns
2. **HTML Collection**: Downloads all linked HTML pages
3. **Asset Scanning**: Thoroughly scans HTML for all asset references
4. **Batch Asset Download**: Efficiently downloads all assets while preserving original paths
5. **Directory Structure Creation**: Recreates exact template directory structure

## 🖥️ Live Display

The cloner provides a dynamic terminal interface that displays:

- **Real-time Status**: Animated spinner showing current operation
- **Current File**: Name and status of file being processed
- **Progress Bar**: Visual representation of download progress
- **Download Metrics**: Speed, size, and estimated time remaining
- **Statistics**: Pages processed, resources downloaded, errors, and skipped files

## 📥 Installation

### Requirements
- Python 3.7 or higher
- Required packages: requests, beautifulsoup4, rich

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/NYTEMODEONLY/website-cloner-enhanced.git
   cd website-cloner-enhanced
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🔧 Usage

### Basic Usage

```bash
python website_cloner.py [URL]
```

### Advanced Options

```bash
python website_cloner.py [URL] -o [OUTPUT_FOLDER] --min-delay [MIN] --max-delay [MAX] --debug
```

Parameters:
- `URL`: Target website URL (required)
- `-o, --output`: Output folder (default: "cloned_website")
- `--min-delay`: Minimum delay between requests in seconds (default: 1.0)
- `--max-delay`: Maximum delay between requests in seconds (default: 3.0)
- `--debug`: Enable verbose debug logging

### Examples

Clone a standard website:
```bash
python website_cloner.py https://example.com -o example_clone
```

Clone a template website with increased delays:
```bash
python website_cloner.py https://template-site.com/HTML/demo/index.html --min-delay 2 --max-delay 5
```

Debug mode with custom output folder:
```bash
python website_cloner.py https://website.com -o website_backup --debug
```

## 📈 Roadmap: Planned Updates

We're continuously improving Website Cloner Enhanced with new features and capabilities:

### Coming Soon (Next Release)
- Depth limiting to control crawl scope
- Parallel downloads using async/threading for increased speed
- Domain filtering options for selective crawling

### Medium-term Goals
- JavaScript-rendered content support for modern web applications
- Cookie/session handling for authenticated websites
- Resume capability for interrupted downloads
- Robots.txt compliance and sitemap support

### Long-term Vision
- GUI interface with live visualization
- Scheduled cloning and change detection
- Integration with web archiving standards
- PDF export and offline documentation generation

See our [Tasks.md](tasks.md) file for a detailed development plan.

## 🛠️ Troubleshooting

### Common Issues

- **SSL Certificate Errors**: Adjust your Python SSL configuration or use `--ignore-ssl` option
- **Access Denied Errors**: Some websites prevent automated access; try adjusting request delays
- **Missing Resources**: Modern websites may load resources dynamically; check debug logs for insights
- **Memory Issues on Large Sites**: Use depth limiting on very large websites

### Debug Mode

Enable debug mode for detailed logging:
```bash
python website_cloner.py [URL] --debug
```

Logs are saved in the `logs/` directory for further analysis.

## 🤝 Contributing

Contributions to the Website Cloner Enhanced are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b new-feature`
3. Commit your changes: `git commit -am 'Add new feature'`
4. Push to the branch: `git push origin new-feature`
5. Submit a pull request

Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📣 Acknowledgments

- BeautifulSoup4 for HTML parsing
- Requests library for HTTP handling
- Rich library for terminal UI
- Original concept inspired by various web archiving tools

---

<p align="center">
  Forked with ❤️ by <a href="https://nytemode.com">NYTEMODE</a>
</p>
