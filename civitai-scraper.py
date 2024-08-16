
import os
import re
import time
import logging
from multiprocessing import Pool
from io import BytesIO

import click
import requests

import pillow_avif
from PIL import Image, UnidentifiedImageError

INITIAL_URL = "https://civitai.com/api/v1/images?sort=Newest"
DEFAULT_WORKERS = 16

# Regex to clean up prompt text
TAG_REGEX = re.compile(r'<.*?>')


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
    if item['meta'] is not None:
        return "prompt" in item['meta']

    return False


def contains_keywords(item, require_keywords):
    if not has_prompt(item):
        return False

    # Skip items that do not contain a specific prompt
    if require_keywords != "":
        for keyword in require_keywords.split(","):
            if str(keyword).strip() in item['meta']['prompt']:
                return True

    return False


def should_ignore(item, ignore_keywords):
    if not has_prompt(item):
        return False

    # Skip items that contain a specific prompt
    if ignore_keywords != "":
        for keyword in ignore_keywords.split(","):
            if str(keyword).strip() in item['meta']['prompt']:
                return True

    return False


def download_file(url, identifier, filepath, extension, compress=False, avif=False):
    # Download the next item (image/video)
    item_response = requests.get(url)

    def write_raw_response():
        with open(os.path.join(filepath, f"{identifier}.{extension}"), "wb") as file:
            file.write(item_response.content)

    # Attempt to download an image (not all URLs are images)
    if compress is True or avif is True:
        try:
            image = Image.open(BytesIO(item_response.content))

            # Convert image to RGB if necessary
            if image.mode in ['RGBA', 'P']:
                image = image.convert('RGB')

            if avif:
                image.save(os.path.join(
                    filepath, f"{identifier}.avif"),
                    quality=70 if compress else 100,
                    lossless=False if compress else True
                )
            else:
                # We need to specify the file extension as jpg for pillow.
                image.save(os.path.join(
                    filepath, f"{identifier}.jpg"),
                    optimize=True,
                    quality=80
                )

        except UnidentifiedImageError:
            write_raw_response()

    else:
        write_raw_response()

    logging.info(f"Downloaded {identifier}.")


def download_item(item, output_path, compress, avif, segment_by_date, segment_by_rating, require_keywords, ignore_keywords):
    identifier = item['id']

    url = item['url']

    # Get the file extension
    extension = re.search(r'\.([a-zA-Z0-9]+)$', url).group(1)

    # Prepare the file path which will be optionally segmented
    filepath = os.path.join(output_path)

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

    if has_prompt(item):
        # Skip images that contain specific prompt keywords
        if should_ignore(item, ignore_keywords):
            return {
                "error": None,
                "ignored": True,
                "identifier": identifier,
                "url": url,
            }

        if require_keywords != "" and not contains_keywords(item, require_keywords):
            return {
                "error": None,
                "ignored": True,
                "identifier": identifier,
                "url": url,
            }

        # Save meta.prompt as a text file if the prompt exists
        meta_prompt = TAG_REGEX.sub('', item['meta']['prompt'])
        meta_filename = os.path.join(
            filepath, f"{identifier}.txt")

        with open(meta_filename, "w", encoding='utf-8') as meta_file:
            meta_file.write(meta_prompt)

    try:
        download_file(
            url,
            identifier,
            filepath,
            extension,
            compress,
            avif
        )

    except Exception as e:
        return {
            "error": e,
            "ignored": False,
            "identifier": identifier,
            "url": url,
        }

    return {
        "error": None,
        "ignored": False,
        "identifier": identifier,
        "url": url,
    }


@click.command()
@click.option("-d", "--debug", default=False, help="Enable debug logging")
@click.option("-s", "--silent", default=False, help="Disable logging")
@click.option("-k", "--api-key", help="API key for Civitai", required=True)
@click.option("-o", "--output-path", default=".", help="Path to save the images")
@click.option("-z", "--compress", default=False, help="Compress images to reduce file size", is_flag=True)
@click.option("-w", "--workers", default=DEFAULT_WORKERS, help="Number of workers to use for downloading")
@click.option("-l", "--limit",  default=0, help="Maximum number of images to download")
@click.option("-c", "--cursor", help="Cursor to start downloading from")
@click.option("--min-width", default=0, help="Minimum width of the image")
@click.option("--min-height", default=0, help="Minimum height of the image")
@click.option("--min-like", default=0, help="Minimum number of likes")
@click.option("--min-dislike", default=0, help="Minimum number of dislikes")
@click.option("--min-comment", default=0, help="Minimum number of comments")
@click.option("--min-hearts", default=0, help="Minimum number of hearts")
@click.option("--min-cry", default=0, help="Minimum number of cry reactions")
@click.option("--min-laugh", default=0, help="Minimum number of laugh reactions")
@click.option("--require-metadata", default=False, help="Only download images with metadata")
@click.option("--require-keywords", default="", help="CSV of keywords to match the prompt and require")
@click.option("--ignore-keywords", default="", help="CSV of keywords to match the prompt and ignore")
@click.option("--nsfw", default=False, help="Include NSFW images")
@click.option("--nsfw-only", default=False, help="Only download NSFW images")
@click.option("--segment-by-date", default=False, help="Segment images into directories by date", is_flag=True)
@click.option("--segment-by-rating", default=False, help="Segment images into directories by rating", is_flag=True)
@click.option("--avif", is_flag=True, help="Save images in AVIF")
def scrape(
        debug,
        silent,
        api_key,
        output_path,
        compress,
        limit,
        workers,
        cursor,
        min_width,
        min_height,
        min_like,
        min_dislike,
        min_comment,
        min_hearts,
        min_cry,
        min_laugh,
        require_metadata,
        require_keywords,
        ignore_keywords,
        nsfw,
        nsfw_only,
        segment_by_date,
        segment_by_rating,
        avif
):
    """Download images from Civitai API."""

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if silent:
        logging.getLogger().setLevel(logging.CRITICAL)

    # Authentication headers
    headers = {"Authorization": f"Bearer {api_key}"}

    # Append NSFW filter to the API endpoint
    api_endpoint = INITIAL_URL
    if nsfw_only:
        api_endpoint += "&nsfw=true"

    elif nsfw:
        api_endpoint += "&nsfw=X"

    else:
        api_endpoint += "&nsfw=false"

    # Append cursor to the API endpoint
    if cursor:
        api_endpoint += f"&cursor={cursor}"

    # Ensure directory exists
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Store downloaded URLs to avoid duplicates
    downloaded_urls_path = os.path.join(output_path, "downloaded.log")
    downloaded_urls = set()

    # Load downloaded URLs
    if os.path.exists(downloaded_urls_path):
        with open(downloaded_urls_path) as log_file:
            downloaded_urls = set(log_file.readlines())

    next_cursor = cursor

    # Download images
    with open(downloaded_urls_path, "a") as log_file:
        next_url = api_endpoint
        total_saved = 0

        while next_url and (limit == 0 or total_saved < limit):
            success = False
            retry_count = 0

            while not success and retry_count < 3:
                response = requests.get(next_url, headers=headers)

                try:
                    response_json = response.json()

                    success = True

                except requests.JSONDecodeError as e:
                    logging.error(f"Failed to decode JSON response: {e}")
                    logging.debug(f"Response: {response.text}")

                    retry_count += 1

                    logging.info(
                        f"Retrying in 30 seconds... (Attempt {retry_count})"
                    )

                    time.sleep(30)

            if not success:
                logging.fatal(
                    f"Failed to retrieve JSON response after 3 attempts. Exiting..."
                )

                return

            # Get next URL from metadata
            if 'metadata' in response_json and 'nextPage' in response_json['metadata']:
                if next_cursor:
                    logging.info(f"Dowloading images from '{next_cursor}' to '{
                        response_json['metadata']['nextCursor']}'"
                    )
                else:
                    logging.info(f"Dowloading images from the latest entry to '{
                        response_json['metadata']['nextCursor']}'"
                    )

                next_cursor = response_json['metadata']['nextCursor']
                next_url = response_json['metadata']['nextPage']
            else:
                next_url = None

            # Filters passed to the filter_items function
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

            with Pool(workers) as pool:
                results = pool.starmap(
                    download_item,
                    [
                        (
                            item,
                            output_path,
                            compress,
                            avif,
                            segment_by_date,
                            segment_by_rating,
                            require_keywords,
                            ignore_keywords
                        ) for item in filtered_items
                    ]
                )

                for result in results:
                    if result:
                        if result['ignored']:
                            logging.info(f"Ignored {result['identifier']}.")

                        if result['error'] is None:
                            logging.info(f"Downloaded {result['identifier']}.")

                            total_saved += 1

                            log_file.write(f"{result['url']}\n")

                            downloaded_urls.add(result['url'])

                        else:
                            logging.error(
                                f"Failed to download {
                                    result['identifier']}: {result['error']}"
                            )

                if limit != 0 and total_saved >= limit:
                    break

    logging.info(
        f"Downloaded and saved {total_saved} images/videos and metadata files."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    scrape(auto_envvar_prefix='CIVITAI_SCRAPER')
