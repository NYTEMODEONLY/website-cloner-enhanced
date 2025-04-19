import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urljoin, urlparse
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.panel import Panel

# Initialize rich console
console = Console()

# Define headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def ensure_directory(path):
    """Create directory and any missing parent directories"""
    os.makedirs(path, exist_ok=True)

def download_file(url, output_path, progress=None, task_id=None):
    """Download a file with progress tracking"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Skip if file exists
        if os.path.exists(output_path):
            if progress:
                progress.advance(task_id)
            return True

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
                    if progress and task_id:
                        progress.update(task_id, completed=downloaded)
                        
        return True
    except Exception as e:
        console.print(f"[red]Failed to download {url}: {e}[/red]")
        return False

def clone_template_site(url, output_dir):
    """Clone a template-style website with assets in relative paths"""
    console.print(Panel.fit(
        f"[bold cyan]Template Website Cloner[/bold cyan]\n\n"
        f"[green]URL:[/green] {url}\n"
        f"[green]Output:[/green] {output_dir}",
        title="Starting Template Clone",
        border_style="blue"
    ))
    
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
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    # Save the main HTML file
    filename = os.path.basename(parsed_url.path) or 'index.html'
    main_html_path = os.path.join(output_dir, filename)
    
    with open(main_html_path, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    console.print(f"[green]Downloaded main HTML:[/green] {filename}")
    
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
    
    console.print(f"[green]Found {len(asset_links)} assets to download[/green]")
    
    # Setup progress display
    progress_columns = [
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn()
    ]
    
    # Download all assets with progress tracking
    with Progress(*progress_columns, console=console) as progress:
        overall_task = progress.add_task("[cyan]Overall progress", total=len(asset_links))
        
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
            
            # Create download task
            task_description = f"Downloading: {asset_path}"
            task_id = progress.add_task(task_description, total=100)
            
            # Download the file
            success = download_file(asset_url, local_path, progress, task_id)
            
            # Update overall progress
            progress.advance(overall_task)
    
    # Find and download HTML pages linked from the main page
    html_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Only include relative links that likely point to HTML pages
        if (href.endswith('.html') or '.' not in os.path.basename(href)) and not href.startswith(('http://', 'https://', '#')):
            html_links.append(href)
    
    # Remove duplicates
    html_links = list(set(html_links))
    
    if html_links:
        console.print(f"[green]Found {len(html_links)} additional HTML pages to download[/green]")
        
        with Progress(*progress_columns, console=console) as progress:
            html_task = progress.add_task("[cyan]Downloading HTML pages", total=len(html_links))
            
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
                
                # Create task for this HTML file
                task_description = f"Downloading: {html_path}"
                task_id = progress.add_task(task_description, total=100)
                
                # Download the HTML file
                try:
                    response = requests.get(html_url, headers=headers)
                    response.raise_for_status()
                    
                    # Create directory if needed
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    
                    # Save the HTML file
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    
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
                        
                        # Download without detailed progress
                        ensure_directory(os.path.dirname(sub_local_path))
                        if not os.path.exists(sub_local_path):
                            try:
                                r = requests.get(asset_url, headers=headers)
                                r.raise_for_status()
                                with open(sub_local_path, 'wb') as f:
                                    f.write(r.content)
                            except Exception as e:
                                console.print(f"[red]Failed to download sub-asset {asset_url}: {e}[/red]")
                    
                    progress.update(task_id, completed=100)
                except Exception as e:
                    console.print(f"[red]Failed to download HTML page {html_url}: {e}[/red]")
                    progress.update(task_id, completed=100)
                
                progress.advance(html_task)
    
    console.print(Panel.fit(
        f"[bold green]Template website clone completed![/bold green]\n\n"
        f"[cyan]Files downloaded:[/cyan] [green]{len(asset_links)}[/green] assets, [green]{len(html_links)}[/green] HTML pages\n"
        f"[cyan]Output directory:[/cyan] [green]{output_dir}[/green]",
        title="Clone Complete",
        border_style="green"
    ))

if __name__ == "__main__":
    url = "https://wpriverthemes.com/HTML/boldz/index.html"
    output_dir = "cloned_website"
    
    # Start timing
    start_time = time.time()
    
    # Run the cloner
    clone_template_site(url, output_dir)
    
    # Print elapsed time
    elapsed = time.time() - start_time
    console.print(f"[green]Cloning completed in {elapsed:.2f} seconds[/green]") 