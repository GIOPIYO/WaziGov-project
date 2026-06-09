#!/bin/bash
# WaziGov Kaggle Script Uploader
# Bundles inference, evaluation, and training scripts into a Kaggle Dataset.

STAGING_DIR="kaggle_scripts_staging"
DATASET_NAME="wazigov-table-scripts"

echo "1. Creating staging area..."
mkdir -p $STAGING_DIR

# List the specific scripts to include
cp scripts/inference.py $STAGING_DIR/
cp scripts/train_table_detection.py $STAGING_DIR/
# Note: Ensure evaluate.py exists in your scripts folder
if [ -f "scripts/evaluate.py" ]; then
    cp scripts/evaluate.py $STAGING_DIR/
fi

echo "2. Initializing Kaggle Metadata..."
# Generates dataset-metadata.json if it doesn't exist
if [ ! -f "$STAGING_DIR/dataset-metadata.json" ]; then
    kaggle datasets init -p $STAGING_DIR
    
    # Update the title and slug automatically
    # You can change 'YOUR_USERNAME' if the CLI doesn't auto-detect your profile
    sed -i "s/INSERT_TITLE_HERE/WaziGov-Table-Scripts/g" $STAGING_DIR/dataset-metadata.json
    sed -i "s/INSERT_SLUG_HERE/$DATASET_NAME/g" $STAGING_DIR/dataset-metadata.json
fi

echo "3. Uploading to Kaggle..."
# Try to create the dataset. If it exists, it will fail, and we will push a new version instead.
if kaggle datasets create -p $STAGING_DIR --public; then
    echo "Successfully created new dataset: $DATASET_NAME"
else
    echo "Dataset exists. Pushing a new version..."
    kaggle datasets version -p $STAGING_DIR -m "Updated WaziGov scripts: $(date +%Y-%m-%d)"
fi

echo "Done. You can now find your scripts at: https://www.kaggle.com/datasets/<your-username>/$DATASET_NAME"