
# civitai-scraper

Downloads bulk images/videos from Civitai with filtering options and directory segmentation.

## Usage

Create a new virtual environment and install required modules by running the following commands.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the script with the following command.

```bash
python3 civitai-scraper.py --help

Usage: civitai-scraper.py [OPTIONS]

  Download images from Civitai API.

Options:
  -d, --debug BOOLEAN         Enable debug logging
  -s, --silent BOOLEAN        Disable logging
  -k, --api-key TEXT          API key for Civitai  [required]
  -p, --download-path TEXT    Path to save the images
  -w, --workers INTEGER       Number of workers to use for downloading
  -l, --limit INTEGER         Maximum number of images to download
  -c, --cursor TEXT           Cursor to start downloading from
  --min-width INTEGER         Minimum width of the image
  --min-height INTEGER        Minimum height of the image
  --min-like INTEGER          Minimum number of likes
  --min-dislike INTEGER       Minimum number of dislikes
  --min-comment INTEGER       Minimum number of comments
  --min-hearts INTEGER        Minimum number of hearts
  --min-cry INTEGER           Minimum number of cry reactions
  --min-laugh INTEGER         Minimum number of laugh reactions
  --require-metadata BOOLEAN  Only download images with metadata
  --ignore-keywords TEXT      CSV of keywords to match the prompt and ignore
  --nsfw BOOLEAN              Include NSFW images
  --nsfw-only BOOLEAN         Only download NSFW images
  --segment-by-date           Segment images into directories by date
  --segment-by-rating         Segment images into directories by rating
  --help                      Show this message and exit.
```
