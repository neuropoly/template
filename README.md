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
export PYTHONPATH="${PYTHONPATH}:path/to/nist_mni_pipelines/ipl/"
export PYTHONPATH="${PYTHONPATH}:path/to/nist_mni_pipelines/ipl"
```

You will also need to install `scoop` with: `pip install scoop`

For some reason, the latest version of scoop is not completely compatible with IPL scripts. Briefly, the `scoop.futures:submit()` function does not accept arguments with names. You may have to change the following lines of the script `nist_mni_pipelines/ipl/model/generate_nonlinear.py`:

- 89
- 134-195
- 215
- 227-237
- 254
- 266

For example the lines 180-195 become:
```
else:
    transforms.append(
        futures.submit(
            non_linear_register_step,
            s,
            current_model,
            sample_xfm,
            sample_inv_xfm,
            prev_transform,
            p['level'],
            start,
            symmetric,
            parameters,
            prefix,
            downsample)
        )
```

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
