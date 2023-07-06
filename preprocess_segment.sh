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

# The following global variables are retrieved from the caller sct_run_batch
# but could be overwritten by uncommenting the lines below:
#PATH_DATA_PROCESSED="/Users/nadiablostein/Desktop/multi_subject/test/derivatives/sct_deepseg_labels"
#PATH_RESULTS="/Users/nadiablostein/Desktop/multi_subject/test/derivatives/sct_deepseg_labels/results"
#PATH_LOG="/Users/nadiablostein/Desktop/multi_subject/test/derivatives/sct_deepseg_labels/log"
#PATH_QC="/Users/nadiablostein/Desktop/multi_subject/test/derivatives/sct_deepseg_labels/qc"


# BASH SETTINGS
# ======================================================================================================================

SUFFIX_T2w = "rec-composed_T2w"
SUFFIX_T1w = "rec-composed_T1w"

# Uncomment for full verbose
# set -v

# Immediately exit if error
set -e

# Exit if user presses CTRL+C (Linux) or CMD+C (OSX)
trap "echo Caught Keyboard Interrupt within script. Exiting now.; exit" INT


# CONVENIENCE FUNCTIONS
# ======================================================================================================================

label_if_does_not_exist() {
  ###
  #  This function checks if a manual label file already exists, then:
  #     - If it does, copy it locally.
  #     - If it doesn't, perform automatic labeling.
  #   This allows you to add manual labels on a subject-by-subject basis without disrupting the pipeline.
  ###
  local file="$1"
  local file_seg="$2"
  # Update global variable with segmentation file name
  FILELABEL="${file}_labels"
  echo "Looking for labels: ${FILELABEL}"
  if [[ -e ${FILELABEL}.nii.gz ]]; then
    echo "Found! Using vertebral labels that exist."
  else
    echo "Not found. Proceeding with automatic labeling."
    # Generate labeled segmentation
    sct_label_vertebrae -i ${file}.nii.gz -s ${file_seg}.nii.gz -c t2 -qc "${PATH_QC}" -qc-subject "${SUBJECT}"
  fi
}

segment_if_does_not_exist() {
  ###
  #  This function checks if a manual spinal cord segmentation file already exists, then:
  #    - If it does, copy it locally.
  #    - If it doesn't, perform automatic spinal cord segmentation.
  #  This allows you to add manual segmentations on a subject-by-subject basis without disrupting the pipeline.
  ###
  local file="$1"
  local contrast="$2"
  # Update global variable with segmentation file name
  FILESEG="${file}_seg"
  echo
  echo "Looking for segmentation: ${FILESEG}"
  if [[ -e ${FILESEG}.nii.gz ]]; then
    echo "Found! Using SC segmentation that exists."
    sct_qc -i ${file}.nii.gz -s ${FILESEG}.nii.gz -p sct_deepseg_sc -qc ${PATH_QC} -qc-subject ${SUBJECT}
  else
    echo "Not found. Proceeding with automatic segmentation."
    # Segment spinal cord
    sct_deepseg_sc -i ${file}.nii.gz -c $contrast -qc ${PATH_QC} -qc-subject ${SUBJECT}
  fi
}

# SCRIPT STARTS HERE
# ======================================================================================================================

# Retrieve input params
SUBJECT=$1

# get starting time:
start=`date +%s`

# Display useful info for the log, such as SCT version, RAM and CPU cores available
sct_check_dependencies -short

# Go to folder where data will be copied and processed
cd $PATH_DATA_PROCESSED
# Copy source images
rsync -avzh $PATH_DATA/$SUBJECT .

# T2w
# ======================================================================================================================
cd "${SUBJECT}/anat/"
file_t2="${SUBJECT}_${SUFFIX_T2w}"
# Segment spinal cord 
segment_if_does_not_exist "${file_t2}" "t2"
file_t2_seg="${FILESEG}"
# Create vertebral labels 
label_if_does_not_exist "${file_t2}" "${file_t2_seg}"

# T1w
# ======================================================================================================================
file_t1="${SUBJECT}_${SUFFIX_T1w}"
# Segment spinal cord 
segment_if_does_not_exist "${file_t1}" "t1"
file_t1_seg="${FILESEG}"
# Create vertebral labels 
label_if_does_not_exist "${file_t1}" "${file_t1_seg}"

# Verify presence of output files and write log file if error
# ======================================================================================================================
FILES_TO_CHECK=(
  "$file_t2_seg.nii.gz"
  "$file_t1_seg.nii.gz"
)
for file in "${FILES_TO_CHECK[@]}"; do
  if [ ! -e "${file}" ]; then
    echo "${SUBJECT}/${file} does not exist" >> "${PATH_LOG}/error.log"
  fi
done

# Display useful info for the log
end=`date +%s`
runtime=$((end-start))
echo
echo "~~~"
echo "SCT version: `sct_version`"
echo "Ran on:      `uname -nsr`"
echo "Duration:    $(($runtime / 3600))hrs $((($runtime / 60) % 60))min $(($runtime % 60))sec"
echo "~~~"

