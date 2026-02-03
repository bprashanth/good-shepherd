## Data upload 

This document describes how data is uploaded to the backend. 

The "backend" for the fomo app has storage in 2 locations:     

1. The mobile app uploads its images to a drive folder. 
2. The forestfomo frontend reads links from the excel given by the user.
3. The excel given by the user has links from s3. 

So how do the images get from drive to s3?     

1. Download the `image_data.json` file in the mobile apps directory. 
2. Run `upload_image_data_json.py --image_data path/to/image_data.json`. This will create an output csv file with links to the images uploaded to s3. 
3. Run `upload_images.py` pointing it at the right root dir with the older images from the restoration sites. This will upload images to s3 and write a different csv file with links to the images. 
4. Combine these csvs (manually) and join it with any existing excel sheets from the user. 
5. Upload the excel via `forestfomo` and start analyzing. 
