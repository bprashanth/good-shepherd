# This script will upload images to S3 from a JSON file.
# The json file is created by the logros mobile app.
# The idea is this scripts output matches the output of hack/upload_images.py
# so they can be combined in the same excel and uploaded to forestfomo.
#
# The s3 bucket compatible with this script is created via hack/s3_bucket.py
#
# The JSON file is expected to have the following structure:
# [{
#   "filePath": "path/to/image.jpg",
#   "timestamp": "2025-05-20T11:50:03.049409",
#   "driveUrl": "https://drive.google.com/uc?export=view&id=1X_nlN1ys63B_oFOAHKXRcFX7hXs5LnJv",
#   "referenceImage": "assets/P2R2.JPG",
#   "location": {
#     "latitude": 10.3093088,
#     "longitude": 76.8354796,
#     "compass": "Northeast",
#     "heading": 63.10809326171875
#   },
#   "notes": "some vegetation cover coming up"
# }]
#
# The output will be a CSV file with the following columns:
# date, stationId, referencePointId, image
#
# - date: from timestamp
# - stationId: from referenceImage
# - referencePointId: from referenceImage
# - image: from filePath

import argparse
import json
import os
import re
import requests
import boto3
import csv
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Config
bucket_name = 'forestfomo-images'
region = 'ap-south-1'
base_s3_url = f'https://{bucket_name}.s3.{region}.amazonaws.com'

s3 = boto3.client('s3')


def download_drive_image(drive_url):
    try:
        # Extract file ID from Google Drive URL
        parsed_url = urlparse(drive_url)
        query = parse_qs(parsed_url.query)
        file_id = query.get('id', [None])[0]

        if not file_id:
            print(f"❌ Invalid Google Drive URL: {drive_url}")
            return None

        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(download_url, stream=True)

        if response.status_code == 200:
            return response.content, f"{file_id}.jpg"
        else:
            print(
                f"❌ Failed to download: {drive_url} (status: {response.status_code})")
            return None
    except Exception as e:
        print(f"❌ Error downloading {drive_url}: {e}")
        return None


def main(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)

    rows = []

    for entry in data:
        drive_url = entry.get('driveUrl')
        timestamp = entry.get('timestamp')
        reference_image = entry.get('referenceImage') or ''
        if reference_image:
            # Extract just the filename without extension from the path
            reference_image = os.path.splitext(
                os.path.basename(reference_image))[0]

        if not drive_url:
            continue

        downloaded = download_drive_image(drive_url)
        if not downloaded:
            continue

        content, filename = downloaded

        # Upload to S3
        s3_key = f"mobile_uploads/{filename}"
        try:
            s3.put_object(Bucket=bucket_name, Key=s3_key, Body=content)
        except Exception as e:
            print(f"❌ S3 upload failed for {filename}: {e}")
            continue

        # Extract date
        try:
            date = datetime.fromisoformat(timestamp).strftime('%Y-%m')
        except:
            date = 'unknown'

        s3_url = f"{base_s3_url}/{s3_key}"
        rows.append([date, reference_image, '', s3_url])

    # Write CSV
    with open('output_from_drive.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['date', 'stationId', 'referencePointId', 'image'])
        writer.writerows(rows)

    print("✅ All done! Output written to output_from_drive.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_data', required=True,
                        help='Path to JSON file')
    args = parser.parse_args()
    main(args.image_data)
