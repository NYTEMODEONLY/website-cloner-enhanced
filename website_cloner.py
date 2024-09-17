import requests
from bs4 import BeautifulSoup
import os
import wget
from urllib.parse import urljoin, urlparse

# Define the headers with a common User-Agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def download_resource(url, folder):
    """
    Download a resource from the web and save it to a folder.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)
    local_filename = os.path.join(folder, os.path.basename(urlparse(url).path))
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        with open(local_filename, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        print(f"Failed to download {url}: {e}")
    return local_filename

def clone_website(url, folder):
    """
    Clone a website by downloading its HTML and resources.
    """
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Create the main folder for the website
    if not os.path.exists(folder):
        os.makedirs(folder)

    # Download all CSS files
    for css in soup.find_all('link', {'rel': 'stylesheet'}):
        css_url = urljoin(url, css['href'])
        local_css = download_resource(css_url, os.path.join(folder, 'css'))
        css['href'] = os.path.relpath(local_css, folder)

    # Download all JavaScript files
    for script in soup.find_all('script', {'src': True}):
        script_url = urljoin(url, script['src'])
        local_script = download_resource(script_url, os.path.join(folder, 'js'))
        script['src'] = os.path.relpath(local_script, folder)

    # Download all images
    for img in soup.find_all('img', {'src': True}):
        img_url = urljoin(url, img['src'])
        local_img = download_resource(img_url, os.path.join(folder, 'images'))
        img['src'] = os.path.relpath(local_img, folder)

    # Download all other resources like videos, audio, etc.
    for resource in soup.find_all(['video', 'audio', 'source']):
        if 'src' in resource.attrs:
            resource_url = urljoin(url, resource['src'])
            local_resource = download_resource(resource_url, os.path.join(folder, 'media'))
            resource['src'] = os.path.relpath(local_resource, folder)

    # Save the modified HTML
    html_path = os.path.join(folder, 'index.html')
    with open(html_path, 'w', encoding='utf-8') as file:
        file.write(soup.prettify())

    print(f"Website cloned successfully and saved to {folder}")

if __name__ == "__main__":
    target_url = "https://www.websiteyouwantcopy.com/"
    folder_name = "cloned_website"
    clone_website(target_url, folder_name)
    print("Website cloning complete.")
