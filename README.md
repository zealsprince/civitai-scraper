
# civitai-image-scraper

Downloads bulk images from Civitai

Filters images in the response to only those that include a Prompt, saves the prompt as a caption text file matching the image name.
Outputted results are almost suitable for training.

LORA's are included in prompts so to do is a toggle to remove LORA's from the saved text file, for now you can remove them manually if using this for training

## Usage

Create a new virtual environment and install required modules by running the following commands.

```bash
python3 -m venv venv
source venv/bin/activat
pip install -r requirements.txt
```

Run the script with the following command.

```bash
python3 civitai-image.py --help

Usage: civitai-image.py [OPTIONS]

  Download images from Civitai API.

Options:
  --api-key TEXT              API key for Civitai
  --download-path TEXT        Path to save the images
  --min-width INTEGER         Minimum width of the image
  --min-height INTEGER        Minimum height of the image
  --max-images FLOAT          Maximum number of images to download
  --require-metadata BOOLEAN  Only download images with metadata
  --ignore-keywords TEXT      Comma separate list of keywords to ignore a
                              result for
                              
  --nsfw BOOLEAN              Include NSFW images
  --nsfw-only BOOLEAN         Only download NSFW images
  
  --help                      Show this message and exit.
```
