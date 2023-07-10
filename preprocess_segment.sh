#!/bin/bash
#
# Process data. This script is designed to be run in the folder for a single subject, however 'sct_run_batch' can be
# used to run this script multiple times in parallel across a multi-subject BIDS dataset.
#
# This script only deals with T2w and MT images for example purpose. For a more comprehensive qMRI analysis, see for
# example this script: https://github.com/spine-generic/spine-generic/blob/master/process_data.sh
#
# Usage:
#   ./process_data.sh <SUBJECT>
#
# Example:
#   ./process_data.sh sub-03
#
# Author: Julien Cohen-Adad (modified by Nadia Blostein)


# Parsing .json file (`configuration.json`)
# ======================================================================================================================

json_file="configuration.json"
# Check if the JSON file exists
if [ ! -f "$json_file" ]; then
  echo "JSON file not found: $json_file"
  exit 1
fi

# Read the JSON file
json_data=$(cat "$json_file")


# Global parameters & Bash settings
# ======================================================================================================================

SUBJECT=$1
PATH_DATA=$(echo "$json_data" | sed -n 's/.*"path_data": "\(.*\)".*/\1/p')
DATA_TYPE=$(echo "$json_data" | sed -n 's/.*"data_type": "\(.*\)".*/\1/p')
IMAGE_SUFFIX=$(echo "$json_data" | sed -n 's/.*"suffix_image": "\(.*\)".*/\1/p')
CONTRAST=$(echo "$json_data" | sed -n 's/.*"contrast": "\(.*\)".*/\1/p')
PATH_DATA_PROCESSED="${PATH_DATA}derivatives/labels/${SUBJECT}/${DATA_TYPE}"
PATH_RESULTS="${PATH_DATA}derivatives/labels/results"
PATH_LOG="${PATH_DATA}derivatives/labels/log"
PATH_QC="${PATH_DATA}derivatives/labels/qc"

# Uncomment for full verbose
# set -v

# Immediately exit if error
set -e

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT


# Check if correct directories exist and make them otherwise
# ======================================================================================================================

[ -d ${PATH_DATA_PROCESSED} ] || mkdir -p ${PATH_DATA_PROCESSED}
[ -d ${PATH_RESULTS} ] || mkdir -p ${PATH_RESULTS}
[ -d ${PATH_LOG} ] || mkdir -p ${PATH_LOG}
[ -d ${PATH_QC} ] || mkdir -p ${PATH_QC}


# Script starts here
# ======================================================================================================================

# get starting time:
start=`date +%s`

# Display useful info for the log, such as SCT version, RAM and CPU cores available
sct_check_dependencies -short

# Go to folder where data will be copied and processed
cd $PATH_DATA_PROCESSED

# Copy source images
rsync -avzh $PATH_DATA/$SUBJECT/$DATA_TYPE/* .


# Segment spinal cord (SC) if does not exist
# ======================================================================================================================

FILE="${SUBJECT}${IMAGE_SUFFIX}.nii.gz"
FILESEG="${SUBJECT}${IMAGE_SUFFIX}_label-SC_seg.nii.gz"

echo "Looking for segmentation: ${FILESEG}"
if [[ -e ${FILESEG} ]]; then
  echo "Found! Using SC segmentation that exists."
  sct_qc -i ${FILE} -s ${FILESEG} -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${SUBJECT}
else
  echo "Not found. Proceeding with automatic segmentation."
  # Segment spinal cord
  sct_deepseg_sc -i ${FILE} -o ${FILESEG} -c ${CONTRAST} -qc ${PATH_QC} -qc-subject ${SUBJECT}
fi

# Label discs if do not exist
# ======================================================================================================================

FILELABEL="${PATH_DATA}derivatives/labels/${SUBJECT}/${DATA_TYPE}/${SUBJECT}${IMAGE_SUFFIX}_label-disc.nii.gz"

echo "Looking for disc labels: ${FILELABEL}"
if [[ -e ${FILELABEL} ]]; then
  echo "Found! Using vertebral labels that exist."
else
  echo "Not found. Proceeding with automatic labeling."
  # Generate labeled segmentation
  sct_label_vertebrae -i ${FILE} -s ${FILESEG} -c ${CONTRAST} -qc "${PATH_QC}" -qc-subject "${SUBJECT}"
  mv "${SUBJECT}${IMAGE_SUFFIX}_label-SC_seg_labeled_discs.nii.gz" "${SUBJECT}${IMAGE_SUFFIX}_label-disc.nii.gz"
  mv "${SUBJECT}${IMAGE_SUFFIX}_label-SC_seg_labeled.nii.gz" "${SUBJECT}${IMAGE_SUFFIX}_label-disc_levels.nii.gz"
fi

# Verify presence of output files and write log file if error
# ======================================================================================================================
FILES_TO_CHECK=(
  "$FILESEG"
  "$FILELABEL"
)
for file in "${FILES_TO_CHECK[@]}"; do
  if [ ! -e "${file}" ]; then
    echo "${SUBJECT}/${file} does not exist" >> "${PATH_LOG}/error.log"
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