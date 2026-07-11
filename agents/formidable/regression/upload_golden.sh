#!/usr/bin/env bash
# Upload the frozen regression fixture (source PDF + golden xlsx) to S3.
# The nightly worker reads these from S3, so this must be run once (and again
# whenever the golden standard is updated).
#
# The fixture lives in the form-idable repo's benchmarks/ dir by default;
# override with SOURCE_PDF / GOLDEN_XLSX env vars.
#
# Usage: ./upload_golden.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/../deploy/config.sh"

SOURCE_PDF="${SOURCE_PDF:-$HOME/src/github.com/bprashanth/form-idable/benchmarks/TreePlots20mx20m.pdf}"
GOLDEN_XLSX="${GOLDEN_XLSX:-$HOME/src/github.com/bprashanth/form-idable/benchmarks/TreePlots20mx20m_merged.xlsx}"

PDF_KEY="${S3_PREFIX}/regression/source.pdf"
GOLDEN_KEY="${S3_PREFIX}/regression/golden.xlsx"

for f in "$SOURCE_PDF" "$GOLDEN_XLSX"; do
  [ -f "$f" ] || { echo "ERROR: not found: $f"; exit 1; }
done

echo "→ Uploading fixture to s3://${JOBS_BUCKET}/${S3_PREFIX}/regression/"
aws s3 cp "$SOURCE_PDF"  "s3://${JOBS_BUCKET}/${PDF_KEY}"    --region "$AWS_REGION"
aws s3 cp "$GOLDEN_XLSX" "s3://${JOBS_BUCKET}/${GOLDEN_KEY}" --region "$AWS_REGION"

echo "Done."
echo "  source PDF: s3://${JOBS_BUCKET}/${PDF_KEY}"
echo "  golden:     s3://${JOBS_BUCKET}/${GOLDEN_KEY}"
