# Spinal cord MRI template
Framework for creating unbiased MRI templates of the spinal cord.

## Dependencies
- [Spinal Cord Toolbox (SCT)](https://github.com/neuropoly/spinalcordtoolbox) version 5.8, `commit 7ead83200d7ad9ee5e0d112e77a1d7b894add738`

SCT is used for all preprocessing steps, including extraction of centerline, generation of average centerline in the template space, and straightening/registration of all spinal cord images on the initial template space. The current version of the pipeline uses SCT 5.8 in development mode (commit `7ead83200d7ad9ee5e0d112e77a1d7b894add738`) as we prepare for the release of SCT 6.0.

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

## Dataset structure
The dataset should be arranged according to the BIDS convention. Using the two examples subjects listed in the `configuration.json` template file, this would be as follows:
dataset/
└── dataset_description.json
└── participants.tsv  <-------------------------------- Metadata describing subjects attributes e.g. sex, age, etc.
└── sub-01  <------------------------------------------ Folder enclosing data for subject 1
└── sub-02
└── sub-03
    └── anat <----------------------------------------- `anat` can be replaced by the value of `data_type` in configuration.json
        └── sub-03_T1w.nii.gz  <----------------------- MRI image in NIfTI format; `_T1w` can be replaced by the value of `suffix_image` in configuration.json
        └── sub-03_T1w.json  <------------------------- Metadata including image parameters, MRI vendor, etc.
        └── sub-03_T2w.nii.gz
        └── sub-03_T2w.json
└── derivatives
    └── labels
        └── sub-03
            └── anat
                └── sub-03_T1w_label-SC_seg.nii.gz  <-- Spinal cord segmentation; `_T1w` can be replaced by the value of `suffix_image` in configuration.json
                └── sub-03_T1w_label-disc.nii.gz  <---- Disc labels; `_T1w` can be replaced by the value of `suffix_image` in configuration.json
                └── sub-03_T2w_label-SC_seg.nii.gz
                └── sub-03_T2w_label-disc.nii.gz

## Getting started: data preprocessing

### Segment spinal cord and vertebral discs

Note:
* SCT functions treat your images with bright CSF as "T2w" (i.e. `t2` option) and dark CSF as "T1w" (i.e. `t1` option).
* You can therefore still use SCT even if your images are not actually T1w and T2w.

1. Set up SCT (see [dependencies](#Dependencies)).
1. Update `segment_sc_discs_deepseg.sh`:
	* Make sure to modify the suffix names for your T2w-like and T1w-like images (SUFFIX_T2w, SUFFIX_T1w) on lines 28 and 29 according to the naming convention in your dataset.
	* If you do not have 2 types of images for each subject, make sure to comment out the appropriate code.
2. Update `segmentat_batching_script.sh`:
	* Update the options according to your own dataset.

3. Run:
```
./segment_batching_script.sh # this calls segment_sc_discs_deepseg.sh
```

4. Quality control (QC):
* Spinal cord masks and disc labels can be displayed by opening: `/PATH/TO/dataset/derivatives/labels/qc/index.html`
* See [tutorial](https://spinalcordtoolbox.com/user_section/tutorials/registration-to-template/vertebral-labeling.html) for tips on how to QC and fix disc labels manually.

### Preparing data for template-generation

`template_preprocessing_pipeline.py` contains several functions to preprocess spinal cord MRI data for template generation. Preprocessing includes:
* extracting the spinal cord centerline and compute the vertebral distribution along the spinal cord, for all subjects.
* computing the average centerline, by averaging the position of each intervertebral disks. The average centerline of the spinal cord is straightened and merged with the ICBM152 template.
* generating the initial template space, based on the average centerline and positions of intervertebral disks.
* straightening of all subjects on the initial template space

1. Create a configuration file according to `configuration_template.json`.
2. Determine the integer value corresponding to the label of the lowest disc until which you want your template to go (depends on the lowest disc available in your images, nomenclature can be found [here](https://spinalcordtoolbox.com/user_section/tutorials/registration-to-template/vertebral-labeling/labeling-conventions.html)).
3. Run the following:
```
python template_preprocessing_pipeline.py configuration.json LOWEST_DISC
```
4. One the preprocessing is performed, please check your data. The preprocessing results should be a series of straight images registered in the same space, with all the vertebral levels aligned with each others.

## How to generate your own template?
The template generation framework can be configured by the file "configuration.json", that includes the following variables:
- "path_data": absolute path to the dataset, including all images [correctly structured](#dataset-structure); ends with `/`.
- "subjects": list of subjects names, that must be the same as folder names in the dataset structure (e.g. `sub-101`).
- "data_type": [BIDS data type](https://bids-standard.github.io/bids-starter-kit/folders_and_files/folders.html#datatype), same as subfolder name in dataset structure (e.g. `anat`).
- "contrast": it is related to the contrast that will be called when you use different SCT functions (either `t1` or `t2`) and may not not necessarily correspond to the actual data acquisition (e.g. `t1`).
- "suffix_image": suffix for image data, after subject ID but before file extension (e.g. `_rec-composed_T1w` in `sub-101_rec-composed_T1w.nii.gz`)
– "suffix_label-SC_seg": suffix for binary images of the spinal cord mask, after subject id but before file extension (e.g. `_rec-composed_T1w_label-SC_seg` in `sub-101_rec-composed_T1w_label-SC_seg.nii.gz`)
- "suffix_label-disc": suffix for binary images of the intervertebral disks labeling, after subject id but before file extension (e.g. `_rec-composed_T1w_label-disc` in `sub-101_rec-composed_T1w_label-disc.nii.gz`)

Now, you can generate the template using the IPL pipeline with the following command, where N has to be replace by the number of subjects:

```
python -m scoop -n N -vvv generate_template.py
```

### Setting up on Canada's Alliance CPU cluster to generate template

It is recommended to run the template generation on a large cluster. If you are in Canada, you could make use of [the Alliance](https://alliancecan.ca/en) (formerly Compute Canada), which is a bunch of CPU nodes accessible to researchers in Canada. **Once the preprocessing is complete**, you will generate the template with `generate_template.py`. This will require minctoolkit v2, minc2simple and nist-mni-pipelines. The easiest way to set up is to use Compute Canada and set up your virtual environment (without spinal cord toolbox, since your data should have already been preprocessed by now) as follows:

1. Load the right modules and install packages from pip wheel
```
module load StdEnv/2020  gcc/9.3.0 minc-toolkit/1.9.18.1 python/3.8.10
pip install --upgrade pip
pip install scoop
```

2. Set up NIST-MNI pipelines
```
git clone https://github.com/vfonov/nist_mni_pipelines.git
nano ~/.bashrc
```
add the following:
```
export PYTHONPATH="${PYTHONPATH}:/path/to/nist_mni_pipelines"
export PYTHONPATH="${PYTHONPATH}:/path/to/nist_mni_pipelines/"
export PYTHONPATH="${PYTHONPATH}:/path/to/nist_mni_pipelines/ipl/"
export PYTHONPATH="${PYTHONPATH}:/path/to/nist_mni_pipelines/ipl"
```
```
source ~/.bashrc
```
3. Minc2simple
```
pip install "git+https://github.com/NIST-MNI/minc2-simple.git@develop_new_build#subdirectory=python"
``` 

4. Create my_job.sh
```
#!/bin/bash
python -m scoop -vvv generate_template.py
```

5. Batch on Alliance Canada
```
sbatch --time=24:00:00  --mem-per-cpu 4000 my_job.sh # will probably require batching several times, depending on number of subjects
```

## Licence
This repository is under a MIT licence.
