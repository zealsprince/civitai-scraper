
# civitai-scraper

Downloads bulk images/videos from Civitai with filtering options.

## Usage

Create a new virtual environment and install required modules by running the following commands.

```bash
python3 -m venv venv
source venv/bin/activat
pip install -r requirements.txt
```

Run the script with the following command.

```bash
python3 civitai-scraper.py --help

Usage: civitai-scraper.py [OPTIONS]

  Download images from Civitai API.

Options:
  --api-key TEXT               API key for Civitai
  --download-path TEXT         Path to save the images
  --max-images FLOAT           Maximum number of images to download
  --min-width INTEGER          Minimum width of the image
  --min-height INTEGER         Minimum height of the image
  --require-metadata BOOLEAN   Only download images with metadata
  --ignore-keywords TEXT       CSV of keywords to match the prompt and ignore
  --nsfw BOOLEAN               Include NSFW images
  --nsfw-only BOOLEAN          Only download NSFW images
  --segment-by-date BOOLEAN    Segment images into directories by date
  --segment-by-rating BOOLEAN  Segment images into directories by rating
  --help                       Show this message and exit.
```
