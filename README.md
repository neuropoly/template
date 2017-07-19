# Spinal cord MRI template
Framework for creating unbiased MRI templates of the spinal cord.

## Dependencies
- [Spinal Cord Toolbox (SCT)](https://github.com/neuropoly/spinalcordtoolbox)

SCT is used for all preprocessing steps, including extraction of centerline, generation of average centerline in the template space, and straightening/registration of all spinal cord images on the initial template space.

- ANIMAL registration framework

ANIMAL is used for generating the template, using iterative nonlinear deformation.

## Get started
The script "preprocessing.py" contains several functions to preprocess spinal cord MRI data. Preprocessing includes:
1) extracting the spinal cord centerline and compute the vertebral distribution along the spinal cord, for all subjects.
2) computing the average centerline, by averaging the position of each intervertebral disks. The average centerline of the spinal cord is straightened and merged with the ICBM152 template.
3) generating the initial template space, based on the average centerline and positions of intervertebral disks.
4) straightening of all subjects on the initial template space

A small dataset, containing 5 T1w and T2w images, is available [here](https://osf.io/h73cm/) and is used as example for preprocessing. The dataset is downloaded automatically by the preprocessing script.

## How to generate your own template?
The template generation framework can be configured by the file "configuration.json", that includes the following variables:
- "path_data": absolute path to the dataset, including all images [correctly structured](#dataset-structure).
- "path_template": absolute path to the output folder, in which the final template will be placed.
- "subjects": list of subjects names, that must be the same as folder names in the dataset structure.
- "suffix_centerline": suffix for binary centerline.
- "suffix_disks": suffix for binary images of the intervertebral disks labeling.
- "suffix_segmentation": optional suffix for the spinal cord segmentation, that can be used to register the segmentation on the template space and generate probabilistic atlases.

## Dataset structure
The dataset should be arranged in a structured fashion, as the following:
- subject_name/
    - t1/
        - t1.nii.gz
        - t1{suffix_centerline}.nii.gz
        - t1{suffix_disks}.nii.gz
        - t1{suffix_segmentation}.nii.gz
    - t2/
        - t2.nii.gz
        - t2{suffix_centerline}.nii.gz
        - t2{suffix_disks}.nii.gz
        - t2{suffix_segmentation}.nii.gz
    - dmri/
        - dmri.nii.gz
        - dmri{suffix_centerline}.nii.gz
        - dmri{suffix_disks}.nii.gz
        - bvecs.txt
        - bvals.txt
    - ...

## Licence
This repository is under a MIT licence.