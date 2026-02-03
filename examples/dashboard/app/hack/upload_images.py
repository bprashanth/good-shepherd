# This script will upload images to S3 from a particular directory structure.
# The s3 bucket compatible with this script is created via hack/s3_bucket.py
#
# Here is an outline of the directory structure:
# Starting from root_dir
# ./2024/2024-J12/R1:
#     2025-03-DSCN2975.JPG
#
# This is stored in an csv (output.csv) with 4 columns:
# date, stationId, referencePointId, image
#
# - date: from filename (4 digits-2digits)
# - stationId: from parent directory (P1R1, P1R2, P2R1, P2R2, J12R1, H13R1)
# - referencePointId: from hadcoded mapping, eg P1R1 -> 2019_LA_R1
# - image: from filename

import os
import re
import boto3
import csv

# CONFIG
bucket_name = 'forestfomo-images'
region = 'ap-south-1'
base_s3_url = f'https://{bucket_name}.s3.{region}.amazonaws.com'
root_dir = '/home/desinotorious/Documents/NCF/fv/candura'  # adjust if needed

# Mapping from stationId to referencePointId
reference_point_map = {
    'P1R1': '2019_LA_R1',
    'P1R2': '2019_LA_R2',
    'P2R1': '2019_SM_R1',
    'P2R2': '2019_SM_R2',
    'J12R1': '2024_J12_R1',
    'H13R1': '2024_H13_R1',
}

s3 = boto3.client('s3')
records = []

for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.lower().endswith('.jpg'):
            local_path = os.path.join(dirpath, filename)

            # Upload to S3 (no ACL needed)
            s3_key = os.path.relpath(local_path, root_dir).replace("\\", "/")
            s3.upload_file(local_path, bucket_name, s3_key)

            # Extract date from filename
            date_match = re.search(r'(\d{4}-\d{2})', filename)
            date = date_match.group(1) if date_match else 'unknown'

            # Get stationId from parent directory
            parent_folder = os.path.basename(os.path.dirname(local_path))
            station_match = re.search(r'(?:_|-)([A-Za-z0-9]+)$', parent_folder)
            station_id = station_match.group(
                1) if station_match else parent_folder

            # Construct referencePointId from mapping
            reference_point_id = reference_point_map.get(station_id, '')

            # Construct image URL
            image_url = f'{base_s3_url}/{s3_key}'

            records.append([date, station_id, reference_point_id, image_url])

# Write CSV
with open('output.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['date', 'stationId', 'referencePointId', 'image'])
    writer.writerows(records)

print("Done! CSV saved as 'output.csv' with referencePointId included.")
