# Spinal cord MRI template

Framework for creating MRI templates of the spinal cord. The framework has two distinct pipelines, which has to be run sequentially: [Data preprocessing](#data-preprocessing) and [Template creation](#template-creation). 

> **Important**
> The framework has to be run independently for each contrast. In the end, the generated templates across contrasts should be perfectly aligned. This is what was done for the PAM50 template.


### [ANIMAL registration framework](https://github.com/vfonov/nist_mni_pipelines)

ANIMAL, part of the IPL longitudinal pipeline, is used for generating the template, using iterative nonlinear deformation.
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

### [Minc Toolkit v2](http://bic-mni.github.io/)

The Minc Toolkit is a dependency of the template generation process.

You will also need to install `scoop` with: `pip install scoop`

On macOs, you may need to recompile Minc Toolkit from source to make sure all libraires are linked correctly.

On Linux: TODO

### [minc2_simple](https://github.com/vfonov/minc2-simple)

Install this python library in SCT python.

## Dataset structure
The dataset should be arranged according to the BIDS convention. Using the two examples subjects listed in the `configuration.json` template file, this would be as follows:
```
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
```


## Data preprocessing

This pipeline includes the following steps:

TODO: remove detials below
1. Segmentation of SC and disc labeling
2. QC. If seg didn't work, fix SC seg. If disc labeling did not work, fix labeling.
3. `configuration_default.json`: Copy this file and rename it as `configuration.json`. Edit it and modify according to your setup.
4. Extraction of SC centerline, generation of average centerline in the template space, straightening/registration of all spinal cord images on the initial template space. 


### Install SCT

SCT is used for all preprocessing steps. The current version of the pipeline uses SCT development version (commit `7ead83200d7ad9ee5e0d112e77a1d7b894add738`) as we prepare for the release of SCT 6.0.

Once SCT is installed, make sure to activate SCT's virtual environment because the pipeline will use SCT's API functions.

```
source ${SCT_DIR}/python/etc/profile.d/conda.sh
conda activate venv_sct
```

### Edit configuration file

Copy the file `configuration_default.json` and rename it as `configuration.json`. Edit it and modify according to your setup:

- `path_data`: Absolute path to the input [BIDS dataset](#dataset-structure); The path should end with `/`.
- `subjects`: List of subjects to include in the preprocessing, separated with comma.
- `data_type`: [BIDS data type](https://bids-standard.github.io/bids-starter-kit/folders_and_files/folders.html#datatype), same as subfolder name in dataset structure. Typically, it should be "anat".
- `contrast`: Contrast to be used by `sct_deepseg_sc` function.
- `suffix_image`: Suffix for image data, after subject ID but before file extension (e.g. `_rec-composed_T1w` in `sub-101_rec-composed_T1w.nii.gz`)
– `suffix_label-SC_seg`: Suffix for binary images of the spinal cord mask, after `suffix_image` (e.g. `_label-SC_seg`).
- "suffix_label-disc": suffix for binary images of the intervertebral disks labeling, after subject id but before file extension (e.g. `_rec-composed_T1w_label-disc` in `sub-101_rec-composed_T1w_label-disc.nii.gz`)
- 
### Segment spinal cord and vertebral discs

Note that SCT functions treat your images with bright CSF as "T2w" (i.e. `t2` option) and dark CSF as "T1w" (i.e. `t1` option). You can therefore still use SCT even if your images are not actually T1w and T2w.

Run script:
```
sct_run_batch -jobs 10 -path-data "/PATH/TO/dataset" -script segment_sc_discs_deepseg.sh -path-output "/PATH/TO/dataset/derivatives/labels"
```

> **Note**
> Replace values appropriately based on your setup (eg: -jobs 10 means that 10 CPU-cores are used. If you have 

#### Quality control (QC)

* Spinal cord masks and disc labels can be displayed by opening: `/PATH/TO/dataset/derivatives/labels/qc/index.html`
* See [tutorial](https://spinalcordtoolbox.com/user_section/tutorials/registration-to-template/vertebral-labeling.html) for tips on how to QC and fix disc labels manually.

### Prepare data for template generation

`template_preprocessing_pipeline.py` contains several functions to preprocess spinal cord MRI data for template generation. Preprocessing includes:
* extracting the spinal cord centerline and compute the vertebral distribution along the spinal cord, for all subjects.
* computing the average centerline, by averaging the position of each intervertebral disks. The average centerline of the spinal cord is straightened and merged with the ICBM152 template.
* generating the initial template space, based on the average centerline and positions of intervertebral discs.
* straightening of all subjects on the initial template space

2. Determine the integer value corresponding to the label of the lowest disc until which you want your template to go (depends on the lowest disc available in your images, nomenclature can be found [here](https://spinalcordtoolbox.com/user_section/tutorials/registration-to-template/vertebral-labeling/labeling-conventions.html)).
3. Run:
```
python template_preprocessing_pipeline.py configuration.json LOWEST_DISC
```

4. One the preprocessing is performed, please check your data. The preprocessing results should be a series of straight images registered in the same space, with all the vertebral levels aligned with each others.


## Template creation

### Dependencies for template generation (see [dependencies](#dependencies_anchor))
- [ANIMAL registration framework, part of the IPL longitudinal pipeline](https://github.com/vfonov/nist_mni_pipelines)
- `scoop` (PyPI)
- [Minc Toolkit v2](http://bic-mni.github.io/)
- [minc2_simple](https://github.com/vfonov/minc2-simple)

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
