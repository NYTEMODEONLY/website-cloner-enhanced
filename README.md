# Website Cloner

The Website Cloner is a Python script that downloads an entire website, including its HTML, CSS, JavaScript, images, and other media resources. This tool is useful for archiving websites or offline browsing.

## Features

- **Download HTML**: Saves the main HTML file of the website.
- **Download CSS**: Saves all linked CSS files.
- **Download JavaScript**: Saves all linked JavaScript files.
- **Download Images**: Saves all images.
- **Download Media**: Saves videos, audio, and other media resources.
- **Preserve Folder Structure**: Maintains the directory structure of the original website.

## How It Works

The script uses `requests` to fetch the website's HTML and resources. It uses `BeautifulSoup` to parse the HTML and extract links to CSS, JavaScript, and other resources. The resources are then downloaded and saved in corresponding folders. The script updates the HTML to use the local copies of these resources.

## Setup and Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/adr1an-debug/website-cloner.git
   cd website-cloner

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt

3. Configure the script:
   Open `website_cloner.py` and set the target_url variable to the URL of the website you want to clone.
   Set the `folder_name` variable to the name of the folder where you want to save the cloned website.

4. Run the script:
  'python website_cloner.py'
   The script will download the website and save it in the specified folder.

## Requirements
- Python 3.7+
- requests
- beautifulsoup4

To install the required packages, you can use the following command:
`pip install requests beautifulsoup4`

## License
This project is licensed under the MIT License.
