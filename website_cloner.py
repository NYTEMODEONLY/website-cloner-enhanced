import requests
from bs4 import BeautifulSoup
import os
import re
import time
import random
import argparse
from urllib.parse import urljoin, urlparse
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.style import Style
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import sys

# Initialize rich console
console = Console()

# Define the headers with a common User-Agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

class WebsiteStats:
    """Track website cloning statistics"""
    def __init__(self):
        self.start_time = time.time()
        self.pages_processed = 0
        self.resources_downloaded = 0
        self.errors = 0
        self.skipped = 0
        self.unique_urls = set()
        self.verified_paths = set()
        self.invalid_paths = set()
        self.current_url = ""
        self.current_file = ""
        self.status = "Initializing..."
        self.total_size = 0
        self.downloaded_size = 0
        self.download_speed = 0
        self.last_update_time = time.time()
        self.last_downloaded_size = 0
        self.rate_limit_message = ""
        self.spinner_index = 0
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.last_spinner_update = time.time()
        
    def update_status(self, status):
        self.status = status
        
    def update_current_file(self, file_path):
        self.current_file = file_path
        
    def update_rate_limit(self, message):
        self.rate_limit_message = message
        
    def get_spinner(self):
        # Update spinner every 0.1 seconds regardless of method calls
        current_time = time.time()
        if current_time - self.last_spinner_update >= 0.1:
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
            self.last_spinner_update = current_time
        return self.spinner_chars[self.spinner_index]
        
    def add_processed(self):
        self.pages_processed += 1
        
    def add_resource(self, size=0):
        self.resources_downloaded += 1
        self.total_size += size
        self.update_download_speed(size)
        
    def add_error(self):
        self.errors += 1
        
    def add_skipped(self):
        self.skipped += 1
        
    def add_url(self, url):
        self.unique_urls.add(url)
        
    def update_download_speed(self, size):
        current_time = time.time()
        time_diff = current_time - self.last_update_time
        
        if time_diff >= 1.0:  # Update speed every second
            self.download_speed = (self.downloaded_size - self.last_downloaded_size) / time_diff
            self.last_downloaded_size = self.downloaded_size
            self.last_update_time = current_time
        
        self.downloaded_size += size
        
    def get_elapsed_time(self):
        return timedelta(seconds=int(time.time() - self.start_time))
        
    def get_estimated_time_remaining(self):
        if self.download_speed > 0 and self.total_size > self.downloaded_size:
            remaining_size = self.total_size - self.downloaded_size
            return timedelta(seconds=int(remaining_size / self.download_speed))
        return timedelta(seconds=0)
        
    def get_progress_percentage(self):
        if self.total_size > 0:
            return (self.downloaded_size / self.total_size) * 100
        return 0

class RateLimiter:
    """
    A simple rate limiter to control the frequency of web requests.
    """
    def __init__(self, min_delay=1.0, max_delay=3.0, debug=False):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0
        self.debug = debug
        
    def wait(self, stats=None):
        """
        Wait an appropriate amount of time since the last request.
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # If enough time has elapsed, no need to wait
        if elapsed >= self.max_delay:
            wait_time = 0
        else:
            # Calculate a random wait time between min and max delay
            # but subtract the time already elapsed
            wait_time = max(0, random.uniform(self.min_delay, self.max_delay) - elapsed)
        
        if wait_time > 0:
            if stats:
                stats.update_rate_limit(f"Rate limiting: waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
            if stats:
                stats.update_rate_limit("")
            
        self.last_request_time = time.time()

def verify_path_exists(url, rate_limiter=None):
    """
    Verify if a URL path exists by sending a HEAD request.
    Returns True if the path exists, False otherwise.
    """
    try:
        if rate_limiter:
            rate_limiter.wait()
        
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
        return response.status_code == 200
    except:
        return False

def verify_directory_exists(url, rate_limiter=None):
    """
    Verify if a directory exists by checking the parent path.
    """
    parsed = urlparse(url)
    parent_path = os.path.dirname(parsed.path)
    if not parent_path or parent_path == '/':
        return True
    
    parent_url = f"{parsed.scheme}://{parsed.netloc}{parent_path}"
    return verify_path_exists(parent_url, rate_limiter)

def download_resource(url, save_path, rate_limiter=None, stats=None, max_retries=3, live_display=None):
    """
    Download a resource from the web and save it to a specific path.
    """
    # For live updates
    last_update_time = time.time()
    live = live_display
    
    try:
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Skip if file already exists
        if os.path.exists(save_path):
            if stats:
                stats.add_skipped()
                stats.update_current_file(f"Skipped (exists): {os.path.basename(save_path)}")
            return save_path
        
        # Check if we've already verified this path exists or not
        parsed_url = urlparse(url)
        if parsed_url.path in stats.invalid_paths:
            return None
        elif parsed_url.path not in stats.verified_paths:
            # Verify the path exists before attempting to download
            if not verify_path_exists(url, rate_limiter):
                stats.invalid_paths.add(parsed_url.path)
                return None
            stats.verified_paths.add(parsed_url.path)
            
        # Apply rate limiting if configured
        if rate_limiter:
            rate_limiter.wait()
            
        if stats:
            stats.update_current_file(f"Downloading: {os.path.basename(save_path)}")
            
        # Retry loop
        for attempt in range(max_retries):
            try:
                # Get the file with streaming
                response = requests.get(url, headers=headers, stream=True)
                response.raise_for_status()
                
                # Create a temporary file for atomic write
                temp_path = save_path + '.tmp'
                downloaded_size = 0
                
                with open(temp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if stats:
                                stats.update_download_speed(len(chunk))
                                
                                # Update display periodically during downloads
                                if live and time.time() - last_update_time > 0.2:
                                    live.update(get_stats_panel(stats))
                                    last_update_time = time.time()
                
                # Atomic rename
                os.rename(temp_path, save_path)
                
                if stats:
                    stats.add_resource(downloaded_size)
                    stats.update_current_file(f"Completed: {os.path.basename(save_path)}")
                return save_path
                
            except Exception as e:
                if attempt < max_retries - 1:
                    if stats:
                        stats.update_current_file(f"Retry {attempt + 1}/{max_retries}: {os.path.basename(save_path)}")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise e
                    
    except Exception as e:
        if stats:
            stats.add_error()
            stats.update_current_file(f"Error: {os.path.basename(save_path)}")
        if isinstance(e, requests.exceptions.RequestException):
            # Only print 404 errors in debug mode
            if not isinstance(e, requests.exceptions.HTTPError) or e.response.status_code != 404:
                logger.error(f"Failed to download {url}: {e}")
        else:
            logger.error(f"Failed to download {url}: {e}")
        return None

def validate_and_normalize_path(path, is_directory=False):
    """
    Validate and normalize a file path to ensure it's safe and properly formatted.
    """
    # Make sure we're working with a relative path
    path = path.lstrip('/')
    
    # Remove consecutive slashes and normalize, keeping it relative
    normalized = os.path.normpath(path).replace('\\', '/')
    
    # If it's a directory path, ensure it ends with '/'
    if is_directory and not normalized.endswith('/'):
        normalized += '/'
        
    # Ensure no path traversal
    if '..' in normalized:
        segments = normalized.split('/')
        filtered = [seg for seg in segments if seg != '..']
        normalized = '/'.join(filtered)
        
    return normalized

def get_resource_path(url, base_url, base_folder):
    """
    Determine the local path where a resource should be saved.
    """
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    
    # If the resource is from a different domain, save it in an external folder
    if parsed_url.netloc and parsed_url.netloc != parsed_base.netloc:
        folder = os.path.join(base_folder, 'external', parsed_url.netloc)
        filename = os.path.basename(parsed_url.path) or 'index.html'
        return os.path.join(folder, filename)
    
    # For resources on the same domain
    path = parsed_url.path
    
    # Empty path means root
    if not path:
        path = '/'
    
    # Check if this is likely a directory
    is_likely_directory = False
    
    # No extension usually means directory
    if '.' not in os.path.basename(path):
        is_likely_directory = True
    
    # Explicit trailing slash means directory
    if path.endswith('/'):
        is_likely_directory = True
        
    # Root is a directory
    if path == '/':
        is_likely_directory = True
    
    # Normalize the path (ensuring it's relative)
    normalized_path = validate_and_normalize_path(path, is_likely_directory)
    
    # Handle directory paths
    if is_likely_directory:
        # Append index.html to directory paths
        if normalized_path.endswith('/'):
            normalized_path += 'index.html'
        else:
            normalized_path = normalized_path + '/index.html'
    
    # Empty path defaults to index.html
    if not normalized_path:
        normalized_path = 'index.html'
    
    # Make sure the final path is relative and joined properly
    return os.path.normpath(os.path.join(base_folder, normalized_path))

def is_internal_link(url, base_url):
    """
    Check if a URL is internal to the base domain.
    """
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    
    # No domain specified means it's a relative URL, so it's internal
    if not parsed_url.netloc:
        return True
    
    # Same domain means it's internal
    if parsed_url.netloc == parsed_base.netloc:
        # Check if base_url has a path (like /HTML/boldz/) and if url follows this path
        base_path = os.path.dirname(parsed_base.path)
        if base_path and not base_path.endswith('/'):
            base_path += '/'
        
        # If base has a path, make sure the URL's path starts with it
        if base_path and not base_path == '/':
            return parsed_url.path.startswith(base_path)
        return True
        
    return False

def get_base_folder_from_url(base_url, output_folder):
    """
    Determine the base folder structure based on the URL path.
    This preserves the original URL structure in the output folder.
    """
    parsed = urlparse(base_url)
    path = parsed.path
    
    # If path has multiple levels, preserve them in the output
    if path and path != '/':
        # Remove file component if present (like index.html)
        if path.endswith('.html') or path.endswith('.htm'):
            path = os.path.dirname(path)
        
        # Ensure path starts and ends with /
        if not path.startswith('/'):
            path = '/' + path
        if not path.endswith('/'):
            path = path + '/'
            
        # Create the complete path
        parts = path.strip('/').split('/')
        if parts:
            folder_path = os.path.join(output_folder, *parts)
            return folder_path
    
    # Default to just the output folder
    return output_folder

def process_html(html_content, page_url, base_url, base_folder, rate_limiter=None, stats=None, live_display=None):
    """
    Process HTML content: extract links and update resource paths.
    Returns: processed HTML and a list of internal links to follow
    """
    soup = BeautifulSoup(html_content, "html.parser")
    internal_links = []
    
    # Group resources by directory to verify directories exist before attempting downloads
    resource_groups = {}
    
    # For live updates
    last_update_time = time.time()
    live = live_display
    
    # Get base directory of the current page for resolving relative paths
    page_dir = os.path.dirname(urlparse(page_url).path)
    
    def add_to_group(url, element, attr):
        # Handle relative paths with dot (./) notation
        if url.startswith('./'):
            # For ./ paths, resolve relative to the current page directory
            if page_dir:
                url = urljoin(urlparse(page_url).scheme + "://" + urlparse(page_url).netloc + page_dir + '/', url[2:])
            else:
                url = urljoin(page_url, url[2:])
        else:
            url = urljoin(page_url, url)
            
        parsed = urlparse(url)
        dir_path = os.path.dirname(parsed.path)
        if dir_path not in resource_groups:
            resource_groups[dir_path] = []
        resource_groups[dir_path].append((url, element, attr))
        
        # Update display periodically
        nonlocal last_update_time
        if live and stats and time.time() - last_update_time > 0.2:
            stats.update_current_file(f"Analyzing: {os.path.basename(url)}")
            live.update(get_stats_panel(stats))
            last_update_time = time.time()
    
    # Collect all resources first
    # CSS stylesheets
    for css in soup.find_all('link', {'rel': ['stylesheet', 'preload']}):
        if 'href' in css.attrs:
            css_url = css['href']  # Don't use urljoin yet - we'll handle in add_to_group
            add_to_group(css_url, css, 'href')
    
    # Script files
    for script in soup.find_all('script', {'src': True}):
        script_url = script['src']  # Don't use urljoin yet
        add_to_group(script_url, script, 'src')

    # Images
    for img in soup.find_all('img'):
        for attr in ['src', 'data-src']:
            if attr in img.attrs:
                img_url = img[attr]  # Don't use urljoin yet
                add_to_group(img_url, img, attr)
        # Also check srcset attribute for responsive images
        if 'srcset' in img.attrs:
            srcset = img['srcset']
            for src_item in srcset.split(','):
                if src_item.strip():
                    # Extract URL from srcset format (url size)
                    src_parts = src_item.strip().split(' ')
                    if src_parts:
                        img_url = src_parts[0]  # Don't use urljoin yet
                        # Create a temporary element for this url
                        temp_element = soup.new_tag('img')
                        temp_element['src'] = img_url
                        add_to_group(img_url, temp_element, 'src')
    
    # Background images in inline style attributes
    for element in soup.find_all(style=True):
        style = element['style']
        # Look for background-image: url(...) pattern
        url_matches = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style)
        for url_match in url_matches:
            if url_match:
                bg_url = url_match  # Don't use urljoin yet
                # Create a temp attribute for this URL
                element['data-bg-url'] = bg_url
                add_to_group(bg_url, element, 'data-bg-url')
    
    # Other multimedia resources
    for resource in soup.find_all(['video', 'audio', 'source', 'iframe', 'embed', 'object']):
        for attr in ['src', 'data-src', 'data', 'poster']:
            if attr in resource.attrs:
                resource_url = resource[attr]  # Don't use urljoin yet
                add_to_group(resource_url, resource, attr)
    
    # Link and anchor tags - collect for navigation
    for a in soup.find_all('a', href=True):
        link_url = a['href']  # Don't use urljoin yet
        
        # Process URL for internal links check
        processed_url = link_url
        if processed_url.startswith('./'):
            if page_dir:
                processed_url = urljoin(urlparse(page_url).scheme + "://" + urlparse(page_url).netloc + page_dir + '/', processed_url[2:])
            else:
                processed_url = urljoin(page_url, processed_url[2:])
        else:
            processed_url = urljoin(page_url, processed_url)
        
        # Always collect HTML links for internal navigation
        if processed_url.startswith(('http://', 'https://')) and is_internal_link(processed_url, base_url):
            if '#' in processed_url:
                # Remove fragment
                processed_url = processed_url.split('#')[0]
            if processed_url:  # Skip empty URLs
                internal_links.append(processed_url)
        
        # Also check if the href is pointing to a resource (non-HTML file)
        # Common resource extensions that should be downloaded
        resource_extensions = ['.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg', 
                            '.webp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
                            '.zip', '.rar', '.mp3', '.mp4', '.webm', '.ogg', '.wav',
                            '.ttf', '.woff', '.woff2', '.eot', '.ico', '.json', '.xml']
        
        if any(processed_url.lower().endswith(ext) for ext in resource_extensions):
            add_to_group(link_url, a, 'href')
    
    # Favicons and other link resources
    for link in soup.find_all('link'):
        if 'href' in link.attrs and link.get('rel'):
            # Handle favicons, manifest, and other resources
            rel = ' '.join(link['rel']).lower()
            if any(rel_type in rel for rel_type in ['icon', 'manifest', 'apple-touch-icon', 'shortcut']):
                link_url = link['href']  # Don't use urljoin yet
                add_to_group(link_url, link, 'href')
    
    # Process resources by directory
    for dir_path, resources in resource_groups.items():
        # Update display periodically
        if live and stats and time.time() - last_update_time > 0.2:
            stats.update_status(f"Processing directory: {dir_path}")
            live.update(get_stats_panel(stats))
            last_update_time = time.time()
            
        if dir_path:
            # Skip entire directory if we know it's invalid
            if dir_path in stats.invalid_paths:
                continue
            
            # Verify directory exists if we haven't checked it yet
            if dir_path not in stats.verified_paths:
                dir_url = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}{dir_path}"
                if not verify_directory_exists(dir_url, rate_limiter):
                    stats.invalid_paths.add(dir_path)
                    continue
                stats.verified_paths.add(dir_path)
        
        # Process resources in verified directories
        for url, element, attr in resources:
            local_path = get_resource_path(url, base_url, base_folder)
            if download_resource(url, local_path, rate_limiter, stats, live_display=live_display):
                relative_path = os.path.relpath(local_path, os.path.dirname(get_resource_path(page_url, base_url, base_folder)))
                element[attr] = relative_path
                
                # If this was a temp attribute for background image, update the style
                if attr == 'data-bg-url':
                    element['style'] = re.sub(r'url\([\'"]?(.*?)[\'"]?\)', f'url({relative_path})', element['style'])
                    del element['data-bg-url']  # Remove the temporary attribute
    
    # Collect internal links to follow
    for a in soup.find_all('a', href=True):
        # Update display periodically
        if live and stats and time.time() - last_update_time > 0.2:
            stats.update_status(f"Analyzing links: {page_url}")
            live.update(get_stats_panel(stats))
            last_update_time = time.time()
            
        link_url = urljoin(page_url, a['href'])
        
        # Skip fragment links (like #section) and non-HTTP protocols
        if link_url.startswith(('http://', 'https://')) and '#' not in link_url:
            if is_internal_link(link_url, base_url):
                internal_links.append(link_url)
                a['href'] = os.path.relpath(
                    get_resource_path(link_url, base_url, base_folder),
                    os.path.dirname(get_resource_path(page_url, base_url, base_folder))
                )
    
    return soup.prettify(), list(set(internal_links))  # Deduplicate links

def get_stats_panel(stats):
    """Create a panel with current statistics"""
    content = []
    content.append(f"[bold cyan]Status:[/bold cyan] {stats.status} {stats.get_spinner()}")
    content.append("")
    content.append("[bold cyan]Current File:[/bold cyan]")
    content.append(f"[yellow]{stats.current_file}[/yellow]")
    content.append("")
    if stats.rate_limit_message:
        content.append(f"[yellow]{stats.rate_limit_message}[/yellow]")
        content.append("")
    content.append("[bold cyan]Download Progress:[/bold cyan]")
    progress = stats.get_progress_percentage()
    progress_bar = "█" * int(progress / 2) + "░" * (50 - int(progress / 2))
    content.append(f"[green]{progress_bar}[/green] {progress:.1f}%")
    content.append(f"[cyan]Downloaded:[/cyan] [green]{stats.downloaded_size / (1024*1024):.2f} MB[/green]")
    content.append(f"[cyan]Total:[/cyan] [green]{stats.total_size / (1024*1024):.2f} MB[/green]")
    content.append(f"[cyan]Speed:[/cyan] [green]{stats.download_speed / (1024*1024):.2f} MB/s[/green]")
    content.append(f"[cyan]ETA:[/cyan] [green]{stats.get_estimated_time_remaining()}[/green]")
    content.append("")
    content.append("[bold cyan]Statistics:[/bold cyan]")
    content.append(f"[cyan]Pages Processed:[/cyan] [green]{stats.pages_processed}[/green]")
    content.append(f"[cyan]Resources Downloaded:[/cyan] [green]{stats.resources_downloaded}[/green]")
    content.append(f"[cyan]Errors:[/cyan] [red]{stats.errors}[/red]")
    content.append(f"[cyan]Skipped:[/cyan] [yellow]{stats.skipped}[/yellow]")
    content.append(f"[cyan]Unique URLs:[/cyan] [green]{len(stats.unique_urls)}[/green]")
    content.append(f"[cyan]Elapsed Time:[/cyan] [green]{stats.get_elapsed_time()}[/green]")
    
    return Panel(
        "\n".join(content),
        title="Website Cloner Progress",
        border_style="blue"
    )

def get_completion_panel(stats):
    """Create a completion panel with final statistics"""
    content = []
    content.append("[bold green]✓ Website cloning complete![/bold green]")
    content.append("")
    content.append("[bold cyan]Final Statistics:[/bold cyan]")
    content.append(f"[cyan]Pages Processed:[/cyan] [green]{stats.pages_processed}[/green]")
    content.append(f"[cyan]Resources Downloaded:[/cyan] [green]{stats.resources_downloaded}[/green]")
    content.append(f"[cyan]Errors:[/cyan] [red]{stats.errors}[/red]")
    content.append(f"[cyan]Skipped:[/cyan] [yellow]{stats.skipped}[/yellow]")
    content.append(f"[cyan]Unique URLs:[/cyan] [green]{len(stats.unique_urls)}[/green]")
    content.append(f"[cyan]Total Time:[/cyan] [green]{stats.get_elapsed_time()}[/green]")
    
    return Panel(
        "\n".join(content),
        title="Cloning Complete",
        border_style="green"
    )

def setup_logging(log_file='website_cloner.log', debug=False):
    """Set up logging configuration"""
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_path = os.path.join(log_dir, log_file)
    
    # Create logger
    logger = logging.getLogger('website_cloner')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    
    # Create handlers
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(message)s')
    
    # Add formatters to handlers
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def ensure_directory(path):
    """Ensure directory exists with proper permissions"""
    try:
        # If path is a directory that already exists, just return success
        if os.path.isdir(path):
            return True
            
        # If path is a file that exists, create a similar directory
        if os.path.isfile(path):
            # Create a directory with a modified name
            dir_path = path + '_dir'
            os.makedirs(dir_path, exist_ok=True)
            os.chmod(dir_path, 0o755)
            logger.warning(f"File exists at {path}, created directory at {dir_path} instead")
            return True
            
        # Normal case - create the directory
        os.makedirs(path, exist_ok=True)
        # Set permissions to 755 (rwxr-xr-x)
        os.chmod(path, 0o755)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False

def is_template_site(url):
    """
    Detect if a website is a template-style site with relative paths.
    Returns True if the site appears to be a template.
    """
    # Check URL patterns common in template sites
    if '/HTML/' in url or '/html/' in url:
        return True
    
    # Check content for template-style path references
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            content = response.text.lower()
            # Look for common template path patterns
            if './assets/' in content or 'assets/css/' in content or 'assets/js/' in content:
                return True
    except:
        pass
        
    return False

def download_file(url, output_path, rate_limiter=None, stats=None, progress=None, task_id=None):
    """Download a file with progress tracking"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Skip if file exists
        if os.path.exists(output_path):
            if stats:
                stats.add_skipped()
            if progress:
                progress.advance(task_id)
            return True

        # Apply rate limiting if configured
        if rate_limiter:
            rate_limiter.wait(stats)

        # Download the file
        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        
        # Get content length if available
        total_size = int(response.headers.get('content-length', 0)) or None
        
        # Update progress bar total if we have content length
        if progress and task_id and total_size:
            progress.update(task_id, total=total_size)
            
        # Download with progress tracking
        with open(output_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if stats:
                        stats.update_download_speed(len(chunk))
                    if progress and task_id:
                        progress.update(task_id, completed=downloaded)
                        
        if stats:
            stats.add_resource(downloaded)
            
        return True
    except Exception as e:
        if stats:
            stats.add_error()
        logger.error(f"Failed to download {url}: {e}")
        return False

def clone_template_site(url, output_dir, rate_limiter=None, stats=None):
    """Clone a template-style website with assets in relative paths"""
    # Make stats object if not provided
    if stats is None:
        stats = WebsiteStats()
        
    # Parse URL components
    parsed_url = urlparse(url)
    base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    base_path = os.path.dirname(parsed_url.path)
    if not base_path.endswith('/'):
        base_path += '/'
    
    # For URL joining
    base_url = base_domain + base_path
    
    # Create output directory
    ensure_directory(output_dir)
    
    # Download the main page
    if rate_limiter:
        rate_limiter.wait(stats)
    
    stats.update_status(f"Processing template site: {url}")
    stats.update_current_file(f"Downloading main HTML")
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Save the main HTML file
    filename = os.path.basename(parsed_url.path) or 'index.html'
    main_html_path = os.path.join(output_dir, filename)
    
    with open(main_html_path, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    stats.add_processed()
    
    # Parse HTML to extract asset links
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract all asset links
    asset_links = []
    
    # CSS files
    for link in soup.find_all('link', rel='stylesheet'):
        if 'href' in link.attrs:
            asset_links.append(link['href'])
    
    # JavaScript files
    for script in soup.find_all('script', src=True):
        asset_links.append(script['src'])
    
    # Images
    for img in soup.find_all('img', src=True):
        asset_links.append(img['src'])
        
    # Background images in style tags
    for style in soup.find_all('style'):
        bg_urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', style.string or '')
        asset_links.extend(bg_urls)
        
    # Background images in inline styles
    for elem in soup.find_all(style=True):
        bg_urls = re.findall(r'url\([\'"]?(.*?)[\'"]?\)', elem['style'])
        asset_links.extend(bg_urls)
    
    # Other resources like fonts, videos, etc.
    for tag in soup.find_all(['video', 'audio', 'source', 'embed', 'object']):
        for attr in ['src', 'data', 'poster']:
            if attr in tag.attrs:
                asset_links.append(tag[attr])
    
    # Remove duplicates and filter out unwanted URLs
    asset_links = list(set(asset_links))
    asset_links = [link for link in asset_links if link and not link.startswith(('http://', 'https://', 'data:', '#'))]
    
    # Download all assets
    for asset_path in asset_links:
        # Handle relative paths correctly
        if asset_path.startswith('/'):
            # Absolute path from domain root
            asset_url = base_domain + asset_path
            local_path = os.path.join(output_dir, asset_path.lstrip('/'))
        else:
            # Relative path from base directory
            asset_url = urljoin(base_url, asset_path)
            local_path = os.path.join(output_dir, asset_path)
        
        stats.update_current_file(f"Downloading: {asset_path}")
        download_file(asset_url, local_path, rate_limiter, stats)
    
    # Find and download HTML pages linked from the main page
    html_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Only include relative links that likely point to HTML pages
        if (href.endswith('.html') or '.' not in os.path.basename(href)) and not href.startswith(('http://', 'https://', '#')):
            html_links.append(href)
    
    # Remove duplicates
    html_links = list(set(html_links))
    
    # Download and process all linked HTML files
    for html_path in html_links:
        if html_path.startswith('/'):
            # Absolute path from domain root
            html_url = base_domain + html_path
            local_path = os.path.join(output_dir, html_path.lstrip('/'))
        else:
            # Relative path from base directory
            html_url = urljoin(base_url, html_path)
            local_path = os.path.join(output_dir, html_path)
        
        # Handle directory-like paths (without extension)
        if '.' not in os.path.basename(local_path):
            local_path = os.path.join(local_path, 'index.html')
        
        stats.update_current_file(f"Downloading HTML: {html_path}")
        
        # Download the HTML file
        try:
            if rate_limiter:
                rate_limiter.wait(stats)
                
            response = requests.get(html_url, headers=headers)
            response.raise_for_status()
            
            # Create directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Save the HTML file
            with open(local_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            stats.add_processed()
            
            # Parse this HTML to find additional assets
            sub_soup = BeautifulSoup(response.text, 'html.parser')
            sub_assets = []
            
            # CSS files
            for link in sub_soup.find_all('link', rel='stylesheet'):
                if 'href' in link.attrs:
                    sub_assets.append(link['href'])
            
            # JavaScript files
            for script in sub_soup.find_all('script', src=True):
                sub_assets.append(script['src'])
            
            # Images
            for img in sub_soup.find_all('img', src=True):
                sub_assets.append(img['src'])
            
            # Filter and download the additional assets
            sub_assets = list(set(sub_assets))
            sub_assets = [link for link in sub_assets if link and 
                          not link.startswith(('http://', 'https://', 'data:', '#'))]
            
            # Get relative directory for this HTML file
            html_dir = os.path.dirname(html_path)
            
            for sub_asset in sub_assets:
                if sub_asset.startswith('/'):
                    # Absolute path from domain root
                    asset_url = base_domain + sub_asset
                    sub_local_path = os.path.join(output_dir, sub_asset.lstrip('/'))
                else:
                    # Relative path from this HTML file's directory
                    if html_dir:
                        asset_url = urljoin(base_url + html_dir + '/', sub_asset)
                    else:
                        asset_url = urljoin(base_url, sub_asset)
                    sub_local_path = os.path.join(output_dir, html_dir, sub_asset)
                
                stats.update_current_file(f"Downloading sub-asset: {sub_asset}")
                
                # Download without detailed progress
                os.makedirs(os.path.dirname(sub_local_path), exist_ok=True)
                if not os.path.exists(sub_local_path):
                    download_file(asset_url, sub_local_path, rate_limiter, stats)
                    
        except Exception as e:
            stats.add_error()
            logger.error(f"Failed to download HTML page {html_url}: {e}")
    
    return stats

def clone_website(base_url, base_folder, min_delay=1.0, max_delay=3.0, debug=False):
    """
    Clone a website by recursively downloading all pages and resources.
    Automatically detects and handles template-style websites.
    """
    # Initialize logging
    global logger
    logger = setup_logging(debug=debug)
    logger.info(f"Starting website clone: {base_url}")
    
    # Check if base_url has a specific path structure we should preserve
    proper_base_folder = get_base_folder_from_url(base_url, base_folder)
    
    # Initialize rate limiter and stats
    rate_limiter = RateLimiter(min_delay=min_delay, max_delay=max_delay, debug=debug)
    stats = WebsiteStats()
    
    # Parse base_url to get its components
    parsed_base = urlparse(base_url)
    base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
    base_path = os.path.dirname(parsed_base.path)
    if not base_path.endswith('/'):
        base_path += '/'
    
    # Ensure output directory exists
    if not ensure_directory(proper_base_folder):
        logger.error(f"Failed to create output directory: {proper_base_folder}")
        return
    
    # Print initial information
    console.print(Panel.fit(
        f"[bold cyan]Website Cloner[/bold cyan]\n"
        f"[green]URL:[/green] {base_url}\n"
        f"[green]Output:[/green] {base_folder}\n"
        f"[green]Rate Limiting:[/green] {min_delay}s to {max_delay}s",
        title="Starting Website Clone",
        border_style="blue"
    ))
    
    with Live(get_stats_panel(stats), console=console, refresh_per_second=10) as live:
        try:
            # Test initial connection
            stats.update_status("Testing connection...")
            live.update(get_stats_panel(stats))
            logger.info("Testing initial connection...")
            
            response = requests.get(base_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            stats.update_status("Connection successful, detecting site type...")
            logger.info("Connection successful, detecting site type...")
            live.update(get_stats_panel(stats))
            
            # Check if this is a template-style website
            is_template = is_template_site(base_url)
            
            if is_template:
                # Use template site cloning approach
                stats.update_status("Detected template-style website, using specialized cloning...")
                logger.info("Detected template-style website, using specialized cloning...")
                live.update(get_stats_panel(stats))
                
                # Perform template site cloning
                clone_template_site(base_url, proper_base_folder, rate_limiter, stats)
                
                # Keep updating display during processing
                last_update_time = time.time()
                while time.time() - last_update_time < 0.5:
                    stats.get_spinner()  # Update spinner
                    live.update(get_stats_panel(stats))
                    time.sleep(0.1)
                    
            else:
                # For regular websites, use recursive crawling approach
                stats.update_status("Using recursive crawling for standard website...")
                logger.info("Using recursive crawling for standard website...")
                live.update(get_stats_panel(stats))
                
                # Initialize the queue with the base URL
                queue = [base_url]
                
                # Add common asset paths to check
                common_asset_paths = [
                    'assets/', 'css/', 'js/', 'images/', 'img/', 'fonts/',
                    'media/', 'videos/', 'audio/', 'documents/', 'downloads/'
                ]
                
                # Add these paths to the queue to make sure we check them
                for asset_path in common_asset_paths:
                    # Try both the domain root and any subdirectory path
                    asset_url = urljoin(base_domain, asset_path)
                    queue.append(asset_url)
                    
                    # If the base URL has a path component, also try from there
                    if base_path and base_path != '/':
                        asset_url = urljoin(base_domain + base_path, asset_path)
                        queue.append(asset_url)
                
                # Keep track of visited URLs to avoid cycles
                visited = set()
                
                # For spinner updates
                last_spinner_update = time.time()
                
                while queue:
                    current_url = queue.pop(0)
                    
                    # Keep spinner animated regardless of progress
                    current_time = time.time()
                    if current_time - last_spinner_update >= 0.1:
                        stats.get_spinner()  # Forces spinner update
                        live.update(get_stats_panel(stats))
                        last_spinner_update = current_time
                    
                    # Skip if already visited
                    if current_url in visited:
                        continue
                        
                    visited.add(current_url)
                    stats.add_url(current_url)
                    stats.update_status(f"Processing: {current_url}")
                    logger.info(f"Processing URL: {current_url}")
                    live.update(get_stats_panel(stats))
                    
                    try:
                        # Apply rate limiting
                        rate_limiter.wait(stats)
                        
                        response = requests.get(current_url, headers=headers, timeout=10)
                        response.raise_for_status()
                        
                        # Check content type
                        content_type = response.headers.get('Content-Type', '').lower()
                        
                        # Only process HTML-like content for link extraction
                        if not any(html_type in content_type for html_type in ['text/html', 'application/xhtml']):
                            stats.update_status(f"Non-HTML content detected: {current_url}")
                            logger.info(f"Skipping non-HTML content ({content_type}): {current_url}")
                            
                            # For non-HTML content, still save the file but don't process it
                            local_path = get_resource_path(current_url, base_url, proper_base_folder)
                            
                            # Check if directory exists at this path and handle appropriately
                            if os.path.isdir(local_path):
                                # If it's supposed to be a file but a directory exists, create a file with a different name
                                parsed = urlparse(current_url)
                                filename = os.path.basename(parsed.path) or 'index'
                                local_path = os.path.join(os.path.dirname(local_path), f"{filename}.bin")
                            
                            # Ensure directory exists
                            dir_path = os.path.dirname(local_path)
                            if not ensure_directory(dir_path):
                                logger.error(f"Failed to create directory for: {local_path}")
                                continue
                                
                            # Save the raw content without processing
                            with open(local_path, 'wb') as file:
                                file.write(response.content)
                                
                            stats.add_resource(len(response.content))
                            stats.update_status(f"Saved non-HTML content: {current_url}")
                            continue
                            
                        # For HTML content, proceed with normal processing
                        # Determine the local path for this URL
                        local_path = get_resource_path(current_url, base_url, proper_base_folder)
                        stats.update_current_file(f"Processing: {os.path.basename(local_path)}")
                        live.update(get_stats_panel(stats))
                        
                        # Check if directory exists at this path and handle appropriately
                        if os.path.isdir(local_path):
                            # If it's a directory, use index.html inside it
                            local_path = os.path.join(os.path.dirname(local_path), 
                                                    os.path.basename(os.path.dirname(local_path)), 
                                                    'index.html')
                        
                        # Ensure directory exists
                        if not ensure_directory(os.path.dirname(local_path)):
                            logger.error(f"Failed to create directory for: {local_path}")
                            continue
                        
                        # Process the HTML content
                        processed_html, new_links = process_html(response.text, current_url, base_url, proper_base_folder, rate_limiter, stats, live)
                        
                        # Save the processed HTML
                        with open(local_path, 'w', encoding='utf-8') as file:
                            file.write(processed_html)
                            
                        # Add new internal links to the queue
                        for link in new_links:
                            if link not in visited:
                                queue.append(link)
                                
                        stats.add_processed()
                        stats.update_status(f"Completed: {current_url}")
                        logger.info(f"Successfully processed: {current_url}")
                        
                    except requests.exceptions.RequestException as e:
                        stats.add_error()
                        stats.update_status(f"Error: {str(e)}")
                        logger.error(f"Error processing {current_url}: {e}")
                        live.update(get_stats_panel(stats))
                    except Exception as e:
                        stats.add_error()
                        stats.update_status(f"Unexpected error: {str(e)}")
                        logger.error(f"Unexpected error processing {current_url}: {e}")
                        live.update(get_stats_panel(stats))
                    
                    # Update the live display
                    live.update(get_stats_panel(stats))
            
        except requests.exceptions.RequestException as e:
            stats.update_status(f"Initial connection failed: {str(e)}")
            logger.error(f"Failed to connect to {base_url}: {e}")
        except Exception as e:
            stats.update_status(f"Unexpected error: {str(e)}")
            logger.error(f"Unexpected error: {e}")
    
    # Print final statistics
    console.print(get_completion_panel(stats))
    logger.info("Website cloning completed")
    logger.info(f"Final statistics: {stats.pages_processed} pages processed, "
                f"{stats.resources_downloaded} resources downloaded, "
                f"{stats.errors} errors, {stats.skipped} skipped")

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Clone a website by downloading all its resources.")
    parser.add_argument("url", help="The URL of the website to clone")
    parser.add_argument("-o", "--output", dest="output_folder", default="cloned_website", 
                        help="The folder where the cloned website will be saved")
    parser.add_argument("--min-delay", type=float, default=1.0,
                        help="Minimum delay between requests in seconds (default: 1.0)")
    parser.add_argument("--max-delay", type=float, default=3.0,
                        help="Maximum delay between requests in seconds (default: 3.0)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    return parser.parse_args()

if __name__ == "__main__":
    # Parse command line arguments if provided, otherwise use defaults
    try:
        args = parse_arguments()
        target_url = args.url
        folder_name = args.output_folder
        min_delay = args.min_delay
        max_delay = args.max_delay
        debug = args.debug
    except:
        # Default values if no command line arguments are provided
        target_url = "https://html.hixstudio.net/heiko-prev/heiko/index.html"
        folder_name = "cloned_website"
        min_delay = 1.0
        max_delay = 3.0
        debug = False
        console.print("[yellow]No command line arguments provided, using default values.[/yellow]")
        console.print("[yellow]To customize, run: python website_cloner.py [URL] -o [OUTPUT_FOLDER] --min-delay [MIN] --max-delay [MAX][/yellow]")
    
    # Use the unified website cloner which automatically detects site type
    clone_website(target_url, folder_name, min_delay, max_delay, debug)
