# Spinal cord MRI template
Framework for creating unbiased MRI templates of the spinal cord.

## Dependencies
- [Spinal Cord Toolbox (SCT)](https://github.com/neuropoly/spinalcordtoolbox)

SCT is used for all preprocessing steps, including extraction of centerline, generation of average centerline in the template space, and straightening/registration of all spinal cord images on the initial template space.

- [ANIMAL registration framework, part of the IPL longitudinal pipeline](https://github.com/vfonov/nist_mni_pipelines)

ANIMAL is used for generating the template, using iterative nonlinear deformation.
The recommanded pipeline for generating a template of the spinal cord is the [nonlinear symmetrical template model](https://github.com/vfonov/nist_mni_pipelines/blob/master/examples/synthetic_tests/test_model_creation/scoop_test_nl_sym.py).

Installation:

`git clone https://github.com/vfonov/nist_mni_pipelines.git`

Add the following lines to you `~/.bashrc` (change the path): 
```
export PYTHONPATH="${PYTHONPATH}:path/to/nist_mni_pipelines"
export PYTHONPATH="${PYTHONPATH}:path/to/nist_mni_pipelines/"
export PYTHONPATH="${PYTHONPATH}:path/to/nist_mni_pipelines/ipl/"
export PYTHONPATH="${PYTHONPATH}:path/to/nist_mni_pipelines/ipl"
```

You will also need to install `scoop` with: `pip install scoop`

- [Minc Toolkit v2](http://bic-mni.github.io/)

The Minc Toolkit is a dependency of the template generation process.

On OSX, you may need to recompile Minc Toolkit from source to make sure all libraires are linked correctly.

- [minc2_simple](https://github.com/vfonov/minc2-simple)

Install this python library in SCT python.

## Get started
The script "pipeline.py" contains several functions to preprocess spinal cord MRI data. Preprocessing includes:
1) extracting the spinal cord centerline and compute the vertebral distribution along the spinal cord, for all subjects.
2) computing the average centerline, by averaging the position of each intervertebral disks. The average centerline of the spinal cord is straightened and merged with the ICBM152 template.
3) generating the initial template space, based on the average centerline and positions of intervertebral disks.
4) straightening of all subjects on the initial template space

A small dataset, containing 5 T1w and T2w images, is available [here](https://osf.io/h73cm/) and is used as example for preprocessing. The dataset is downloaded automatically by the preprocessing script. To use your own dataset and images, follow the section [How to generate your own template?](#how-to-generate-your-own-template). The data preprocessing is performed by running the script `pipeline.py`, after making sure to use SCT python:

```
source sct_launcher
python pipeline.py
```

One the preprocessing is performed, please check your data. The preprocessing results should be a series of straight images registered in the same space, with all the vertebral levels aligned with each others.

Now, you can generate the template using the IPL pipeline with the following command, where N has to be replace by the number of subjects:

```
python -m scoop -n N -vvv generate_template.py
```

## How to generate your own template?
The template generation framework can be configured by the file "configuration.json", that includes the following variables:
- "path_data": absolute path to the dataset, including all images [correctly structured](#dataset-structure); ends with `/`.
- "subjects": list of subjects names, that must be the same as folder names in the dataset structure (e.g. `sub-101`).
- "data_type": [BIDS data type](https://bids-standard.github.io/bids-starter-kit/folders_and_files/folders.html#datatype), same as subfolder name in dataset structure (e.g. `anat`).
- "contrast": it is related to the contrast that will be called when you use different SCT functions (either `t1` or `t2`) and may not not necessarily correspond to the actual data acquisition (e.g. `t1`).
- "suffix_image": suffix for image data, after subject ID but before file extension (e.g. `_rec-composed_T1w` in `sub-101_rec-composed_T1w.nii.gz`)
– "suffix_label-SC_seg": suffix for binary images of the spinal cord mask, after subject id but before file extension (e.g. `_rec-composed_T1w_label-SC_seg` in `sub-101_rec-composed_T1w_label-SC_seg.nii.gz`)
- "suffix_label-disc": suffix for binary images of the intervertebral disks labeling, after subject id but before file extension (e.g. `_rec-composed_T1w_label-disc` in `sub-101_rec-composed_T1w_label-disc.nii.gz`)

## Dataset structure
The dataset should be arranged according to the BIDS convention. Using the two examples subjects listed in the `configuration.json` template file, this would be as follows:
- path_data
    - sub-101
        - data_type
            - 'sub-101' + suffix_image + '.nii.gz'
            - 'sub-101' + suffix_image + '.json'
    - sub-102
        - data_type
            - 'sub-102' + suffix_image + '.nii.gz'
            - 'sub-102' + suffix_image + '.json'
    - ...
    - derivatives
        - sub-101
            - data_type
                - 'sub-101' + suffix_image + suffix_label-SC_seg + '.nii.gz'
                - 'sub-101' + suffix_image + suffix_label-disc + '.nii.gz'
                - 'sub-101' + suffix_image + suffix_label-disc + '-manual.nii.gz' # optional, will automatically be prioritized over non-manual if found!
        - sub-102
            - data_type
                - 'sub-102' + suffix_image + suffix_label-SC_seg + '.nii.gz'
                - 'sub-102' + suffix_image + suffix_label-disc + '.nii.gz'
                - 'sub-102' + suffix_image + suffix_label-disc + '-manual.nii.gz' # optional
        - ...

## Licence
This repository is under a MIT licence.
