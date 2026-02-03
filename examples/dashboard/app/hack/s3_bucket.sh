# This script runs standalone and creates the forestfomo-images bucket. 
# It assumes the aws cli has already been authenticated with the cloud. 
# Usage: 
#     ./s3_bucket.sh	


# Create the bucket (replace with your bucket name and region)
# If this fails: aws s3api delete-bucket --bucket forestfomo-images --region ap-south-1
aws s3api create-bucket --bucket forestfomo-images --region ap-south-1 --create-bucket-configuration LocationConstraint=ap-south-1

# Allow public folders
aws s3api put-public-access-block \
  --bucket forestfomo-images \
  --public-access-block-configuration '{
    "BlockPublicAcls": false,
    "IgnorePublicAcls": false,
    "BlockPublicPolicy": false,
    "RestrictPublicBuckets": false
  }'


# Make the bucket publicly readable (anyone can access the images)
aws s3api put-bucket-policy --bucket forestfomo-images --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::forestfomo-images/*"
  }]
}'

# Enable static hosting-style URLs if needed (optional, mostly for sites)
aws s3 website s3://forestfomo-images/ --index-document index.html

