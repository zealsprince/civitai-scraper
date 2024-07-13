
import os
import re
import math
from io import BytesIO

import click
import requests

from PIL import Image, UnidentifiedImageError

INITIAL_URL = "https://civitai.com/api/v1/images?sort=Newest"

# TODO: Multi-processing
DEFAULT_WORKERS = 4


class FilterParams:
    def __init__(self, min_width, min_height, min_like, min_dislike, min_comment, min_hearts, min_cry, min_laugh, metadata_required, nsfw_only):
        self.min_width = min_width or 0
        self.min_height = min_height or 0

        self.min_like = min_like or 0
        self.min_dislike = min_dislike or 0
        self.min_comment = min_comment or 0
        self.min_hearts = min_hearts or 0
        self.min_cry = min_cry or 0
        self.min_laugh = min_laugh or 0

        self.metadata_required = metadata_required or False

        self.nsfw_only = nsfw_only or False


def filter_items(items, downloaded, filter_params: FilterParams):
    return [
        item for item in items if
        item['url'] + "\n" not in downloaded and

        item['width'] >= filter_params.min_width and
        item['height'] >= filter_params.min_height and

        item['stats']['likeCount'] >= filter_params.min_like and
        item['stats']['dislikeCount'] >= filter_params.min_dislike and
        item['stats']['commentCount'] >= filter_params.min_comment and
        item['stats']['cryCount'] >= filter_params.min_cry and
        item['stats']['laughCount'] >= filter_params.min_laugh and
        item['stats']['heartCount'] >= filter_params.min_hearts and

        (item['meta'] is not None if filter_params.metadata_required else True) and

        (item['nsfw'] if filter_params.nsfw_only else True)
    ]


def has_prompt(item):
    return item['meta'] is not None and item['meta']['prompt'] is not None


def should_ignore(item, ignore_keywords):
    if not has_prompt(item):
        return False

    # Skip items that contain a specific prompt
    if ignore_keywords != "":
        for keyword in ignore_keywords.split(","):
            if keyword in item['meta']['prompt']:
                return True

    return False


def download(url, identifier, filepath, extension):
    # Download the next item (image/video)
    item_response = requests.get(url)

    # Attempt to download an image (not all URLs are images)
    try:
        image = Image.open(BytesIO(item_response.content))

        # Convert image to RGB if necessary
        if image.mode in ['RGBA', 'P']:
            image = image.convert('RGB')

        # We need to specify the file extension as jpg for pillow.
        image.save(os.path.join(filepath, f"{identifier}.jpg"))

    except UnidentifiedImageError:
        # Write the content to a file
        with open(os.path.join(filepath, f"{identifier}.{extension}"), "wb") as file:
            file.write(item_response.content)


@click.command()
@click.option("--api-key", help="API key for Civitai")
@click.option("--download-path", default=".", help="Path to save the images")
@click.option("--max-images",  default=math.inf, help="Maximum number of images to download")
@click.option("--min-width", default=0, help="Minimum width of the image")
@click.option("--min-height", default=0, help="Minimum height of the image")
@click.option("--min-like", default=0, help="Minimum number of likes")
@click.option("--min-dislike", default=0, help="Minimum number of dislikes")
@click.option("--min-comment", default=0, help="Minimum number of comments")
@click.option("--min-hearts", default=0, help="Minimum number of hearts")
@click.option("--min-cry", default=0, help="Minimum number of cry reactions")
@click.option("--min-laugh", default=0, help="Minimum number of laugh reactions")
@click.option("--require-metadata", default=False, help="Only download images with metadata")
@click.option("--ignore-keywords", default="", help="CSV of keywords to match the prompt and ignore")
@click.option("--nsfw", default=False, help="Include NSFW images")
@click.option("--nsfw-only", default=False, help="Only download NSFW images")
@click.option("--segment-by-date", default=False, help="Segment images into directories by date")
@click.option("--segment-by-rating", default=False, help="Segment images into directories by rating")
def scrape(
        api_key,
        download_path,
        max_images,
        min_width,
        min_height,
        min_like,
        min_dislike,
        min_comment,
        min_hearts,
        min_cry,
        min_laugh,
        require_metadata,
        ignore_keywords,
        nsfw,
        nsfw_only,
        segment_by_date,
        segment_by_rating
):
    """Download images from Civitai API."""
    # Check for API key
    api_key = os.environ.get("CIVITAI_API_KEY") or api_key
    if not api_key:
        print("Please set the CIVITAI_API_KEY environment variable or pass it as an argument via --api-key.")

        return

    # Configuration
    headers = {"Authorization": f"Bearer {api_key}"}

    # Append NSFW filter to the API endpoint
    api_endpoint = INITIAL_URL
    if nsfw_only:
        api_endpoint += "&nsfw=true"

    elif nsfw:
        api_endpoint += "&nsfw=X"

    else:
        api_endpoint += "&nsfw=false"

    # Ensure directory exists
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    # Regex to clean up prompt text
    tag_re = re.compile(r'<.*?>')

    # Store downloaded URLs to avoid duplicates
    downloaded_urls_path = os.path.join(download_path, "downloaded.log")
    downloaded_urls = set()

    # Load downloaded URLs
    if os.path.exists(downloaded_urls_path):
        with open(downloaded_urls_path) as log_file:
            downloaded_urls = set(log_file.readlines())

    # Download images
    with open(downloaded_urls_path, "a") as log_file:
        next_url = api_endpoint
        total_saved = 0

        while next_url and total_saved < max_images:
            response = requests.get(next_url, headers=headers)
            response_json = response.json()

            # Get next URL from metadata
            if 'metadata' in response_json and 'nextPage' in response_json['metadata']:
                next_url = response_json['metadata']['nextPage']
            else:
                next_url = None

            filters = FilterParams(
                min_width,
                min_height,
                min_like,
                min_dislike,
                min_comment,
                min_hearts,
                min_cry,
                min_laugh,
                require_metadata,
                nsfw_only
            )

            # Filter images
            filtered_items = filter_items(
                response_json['items'],
                downloaded=downloaded_urls,
                filter_params=filters
            )

            for item in filtered_items:
                identifier = item['id']

                url = item['url']
                extension = re.search(r'\.([a-zA-Z0-9]+)$', url).group(1)

                filename = f"{identifier}.{extension}"
                filepath = os.path.join(download_path)

                if segment_by_date:
                    # Save image in a directory by date
                    date = item['createdAt'].split("T")[0]
                    filepath = os.path.join(
                        filepath, date)

                    if not os.path.exists(filepath):
                        os.makedirs(filepath)

                if segment_by_rating:
                    # Save image in a directory by rating
                    rating = item['nsfwLevel']
                    filepath = os.path.join(
                        filepath, f"{rating}")

                    if not os.path.exists(filepath):
                        os.makedirs(filepath)

                if should_ignore(item, ignore_keywords):
                    print(f"Ignoring image {
                          identifier} due to keyword match in prompt content.")

                    continue

                if has_prompt(item):
                    # Save meta.prompt as a text file.
                    meta_prompt = tag_re.sub('', item['meta']['prompt'])
                    meta_filename = os.path.join(
                        filepath, f"{identifier}.txt")

                    with open(meta_filename, "w", encoding='utf-8') as meta_file:
                        meta_file.write(meta_prompt)

                # Download the image
                download(url, identifier, filepath, extension)

                log_file.write(url + "\n")

                downloaded_urls.add(url)

                total_saved += 1

                if total_saved >= max_images:
                    break

    print(
        f"Downloaded and saved {total_saved} images/videos and metadata files."
    )


if __name__ == "__main__":
    scrape()
