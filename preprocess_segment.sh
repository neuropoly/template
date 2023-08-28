#!/bin/bash
#
# Process data. This script is designed to be run in the folder for a single subject, however 'sct_run_batch' can be
# used to run this script multiple times in parallel across a multi-subject BIDS dataset.
#
# Usage:
#   ./process_data.sh <SUBJECT>
#
# Example:
#   ./process_data.sh sub-03
#
# Author: Julien Cohen-Adad (modified by Nadia Blostein and Rohan Banerjee)


# Uncomment for full verbose
set -x

# Immediately exit if error
set -e -o pipefail

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT

SUBJECT=$1
CONFIG=$2

# Print retrieved variables from the sct_run_batch script to the log (to allow easier debug)
echo "Retrieved variables from from the caller sct_run_batch:"
echo "PATH_DATA: ${PATH_DATA}"
echo "PATH_DATA_PROCESSED: ${PATH_DATA_PROCESSED}"
echo "PATH_RESULTS: ${PATH_RESULTS}"
echo "PATH_LOG: ${PATH_LOG}"
echo "PATH_QC: ${PATH_QC}"
echo "SUBJECT: ${SUBJECT}"
echo "CONFIG FILE PATH: ${CONFIG}"


# Parsing .json file (`configuration.json`)
# ======================================================================================================================
json_file=$CONFIG

# Check if the JSON file exists
if [ ! -f "$json_file" ]; then
  echo "JSON file not found: $json_file"
  exit 1
fi

# Read the JSON file
json_data=$(cat "$json_file")


# Global parameters & Bash settings
# ======================================================================================================================

PATH_DATA=$(echo "$json_data" | sed -n 's/.*"path_data": "\(.*\)".*/\1/p')
DATA_TYPE=$(echo "$json_data" | sed -n 's/.*"data_type": "\(.*\)".*/\1/p')
IMAGE_SUFFIX=$(echo "$json_data" | sed -n 's/.*"suffix_image": "\(.*\)".*/\1/p')
CONTRAST=$(echo "$json_data" | sed -n 's/.*"contrast": "\(.*\)".*/\1/p')
FILE=$PATH_DATA_PROCESSED/$SUBJECT/$DATA_TYPE/${SUBJECT}${IMAGE_SUFFIX}.nii.gz

# Uncomment for full verbose
# set -v

# Immediately exit if error
set -e

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT


# Script starts here
# ======================================================================================================================

# get starting time:
start=`date +%s`

# Display useful info for the log, such as SCT version, RAM and CPU cores available
sct_check_dependencies -short

# Go to folder where data will be copied and processed
mkdir -p $PATH_DATA_PROCESSED/$SUBJECT/$DATA_TYPE
mkdir -p $PATH_DATA_PROCESSED/derivatives/labels/$SUBJECT/$DATA_TYPE
cd $PATH_DATA_PROCESSED/derivatives/labels/$SUBJECT/$DATA_TYPE

# Copy source images
rsync -avzh $PATH_DATA/$SUBJECT/$DATA_TYPE/${SUBJECT}${IMAGE_SUFFIX}.nii.gz $PATH_DATA_PROCESSED/$SUBJECT/$DATA_TYPE


# Segment spinal cord (SC) if does not exist
# ======================================================================================================================

FILESEG="${SUBJECT}${IMAGE_SUFFIX}_label-SC_mask.nii.gz"
sct_deepseg_sc -i ${FILE} -o ${FILESEG} -c ${CONTRAST} -qc ${PATH_QC} -qc-subject ${SUBJECT}

# Label discs if do not exist
# ======================================================================================================================

FILELABEL="${SUBJECT}${IMAGE_SUFFIX}_labeled-discs.nii.gz"
sct_label_vertebrae -i ${FILE} -s "${FILESEG}" -c ${CONTRAST} -qc "${PATH_QC}" -qc-subject "${SUBJECT}"
mv "${SUBJECT}${IMAGE_SUFFIX}_label-SC_mask_labeled_discs.nii.gz" "${FILELABEL}"
rm "${SUBJECT}${IMAGE_SUFFIX}_label-SC_mask_labeled.nii.gz"

# Verify presence of output files and write log file if error
# ======================================================================================================================
FILES_TO_CHECK=(
  "$FILESEG"
  "$FILELABEL" 
)
for file in "${FILES_TO_CHECK[@]}"; do
  if [ ! -e "${file}" ]; then
    echo "${file} does not exist" >> "${PATH_LOG}/error.log"
  fi
done


# Display useful info for the log
# ======================================================================================================================
end=`date +%s`
runtime=$((end-start))
echo
echo "~~~"
echo "SCT version: `sct_version`"
echo "Ran on:      `uname -nsr`"
echo "Duration:    $(($runtime / 3600))hrs $((($runtime / 60) % 60))min $(($runtime % 60))sec"
echo "~~~"
