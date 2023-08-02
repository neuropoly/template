# Spinal cord MRI template

Framework for creating MRI templates of the spinal cord. The framework has two distinct pipelines, which has to be run sequentially: [Data preprocessing](#data-preprocessing) and [Template creation](#template-creation). 

> **Important**
> The framework has to be run independently for each contrast. In the end, the generated templates across contrasts should be perfectly aligned. This is what was done for the PAM50 template.


## Dependencies

### [Spinal Cord Toolbox (SCT)](https://spinalcordtoolbox.com/)

Installation instructions can be found [here](https://spinalcordtoolbox.com/user_section/installation.html).
For the following repository, we used SCT in developper mode (commit `e740edf4c8408ffa44ef7ba23ad068c6d07e4b87`).

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


## Step 1. Data preprocessing

This pipeline includes the following steps:
1. Install SCT;
2. Edit configuration file;
3. Segment spinal cord and vertebral discs;
4. Quality control (QC) segmentation and labels using SCT's web-based HTML QC report, and download YML files of data to be corrected;
5. Manually correct files when correction is needed using the [SCT manual correction](https://spinalcordtoolbox.com/user_section/tutorials/registration-to-template/vertebral-labeling.html) repository;
6. Copy the non-corrected and corrected files back in the input dataset;
7. Normalize spinal cord across subjects;
8. Quality control (QC) spinal cord normalization across subjects.

### 1.1 Install SCT

SCT is used for all preprocessing steps. The current version of the pipeline uses SCT development version (commit `e740edf4c8408ffa44ef7ba23ad068c6d07e4b87`) as we prepare for the release of SCT 6.0.

Once SCT is installed, make sure to activate SCT's virtual environment because the pipeline will use SCT's API functions.

```
source ${SCT_DIR}/python/etc/profile.d/conda.sh
conda activate venv_sct
```

### 1.2 Edit configuration file

Copy the file `configuration_default.json` and rename it as `configuration.json`. Edit it and modify according to your setup:

- `path_data`: Absolute path to the input [BIDS dataset](#dataset-structure); the path should end with `/`.
- `include-list`: List of subjects to include in the preprocessing, separated with a space.
- `data_type`: [BIDS data type](https://bids-standard.github.io/bids-starter-kit/folders_and_files/folders.html#datatype), same as subfolder name in dataset structure. Typically, it should be "anat".
- `contrast`: Contrast to be used by `sct_deepseg_sc` function.
- `suffix_image`: Suffix for image data, after subject ID but before file extension (e.g. `_rec-composed_T1w` in `sub-101_rec-composed_T1w.nii.gz`).
- `first_disc`: Integer value corresponding to the label of the first vertebral disc you want present in the template (see [spinalcordtoolbox labeling conventions](https://spinalcordtoolbox.com/user_section/tutorials/registration-to-template/vertebral-labeling/labeling-conventions.html)).
- `last_disc`: Integer value corresponding to the label of the last vertebral disc you want present in the template.

> **Note**
> Note that SCT functions treat your images with bright CSF as "T2w" (i.e. `t2` option) and dark CSF as "T1w" (i.e. `t1` option). You can therefore still use SCT even if your images are not actually T1w and T2w.

> **Note**
> If you wish to make a template that does not align discs across subjects, please open an [issue](https://github.com/neuropoly/template/issues) and we will follow-up with you.

### 1.3 Segment spinal cord and vertebral discs

Run script:
```
sct_run_batch -script preprocess_segment.sh -config configuration.json -include-list sub-001 sub-002 sub-003 -path-output PATH_OUT -jobs N_CPU
```

With:
- `PATH_OUT`: The location where to output the processed data, results, the logs and the QC information. Example: `/scratch/template_preproc_YYYYMMDD-HHMMSS`. This is a temporary directory in that it is only needed to QC your labels. It therefore cannot be stored inside `path_data`.
- `N_CPU`: The number of CPU cores to dedicate to this task (one subject will be process per core).

> **Note**
> Copy-paste the values to the `include-list` key from `configuration.json` to go after `-include-list` option here.

### 1.4 Quality control (QC) labels

* Spinal cord segmentation (or centerlines) and disc labels can be displayed by opening: `/PATH_OUT/qc/index.html`;
* Quality control (QC) segmentation and labels using [SCT's web-based HTML QC report](https://spinalcordtoolbox.com/overview/concepts/inspecting-results-qc-fsleyes.html#how-do-i-use-the-qc-report), and download YML files (`qc_fail.yml`) of data to be corrected.

### 1.5 Manual correction

Manually correct files when correction is needed, following the [SCT manual correction](https://github.com/spinalcordtoolbox/manual-correction) repository:
* Installation of `manual-correction`
* `manual_correction.py` script:
```
python manual_correction.py -path-img PATH_OUT/data_processed -suffix-files-seg '_label-SC_mask' -suffix-files-seg '_label-SC_mask' -suffix-files-label '_labels-disc' -config path/to/qc_fail.yml
```
* `copy_files_to_derivatives.py` script:
```
python copy_files_to_derivatives.py -path-in PATH_OUT/data_processed/derivatives/labels -path-out path_data/derivatives/labels
```

> **Note**
- `path_data`: from `configuration.json` absolute path to the input [BIDS dataset](#dataset-structure).
- `PATH_OUT`: The location where to output the processed data, results, the logs and the QC information. Example: `/scratch/template_preproc_YYYYMMDD-HHMMSS`. Used in Step 1.3.

> **Note**
> See [tutorial](https://spinalcordtoolbox.com/user_section/tutorials/registration-to-template/vertebral-labeling.html) for tips on how to QC and fix segmentation (or centerline) and/or disc labels manually.

### 1.6 Normalize spinal cord across subjects

`preprocess_normalize.py` contains several functions to normalize the spinal cord across subjects, in preparation for template generation. More specifically:
* Extracting the spinal cord centerline and computing the vertebral distribution along the spinal cord, for all subjects.
* Computing the average centerline, by averaging the position of each intervertebral discs. 
* Straightening the average centerline of the spinal cord.
* Generating the initial template space, based on the average centerline and positions of intervertebral discs,
* Straightening of all subjects' spinal cord on the initial template space.

Run:
```
python preprocess_normalize.py configuration.json
```

### 1.9 Quality control (QC) spinal cord normalization across subjects

One the preprocessing is performed, please check your data. The preprocessing results should be a series of straight images registered in the same space, with all the vertebral levels aligned with each others.


## Step 2. Template creation

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

a) Load the right modules and install packages from pip wheel
```
module load StdEnv/2020  gcc/9.3.0 minc-toolkit/1.9.18.1 python/3.8.10
pip install --upgrade pip
pip install scoop
```

b) Set up NIST-MNI pipelines
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
c) Minc2simple
```
pip install "git+https://github.com/NIST-MNI/minc2-simple.git@develop_new_build#subdirectory=python"
``` 

d) Create `my_job.sh`
```
#!/bin/bash
python -m scoop -vvv generate_template.py
```

e) Batch on Alliance Canada
```
sbatch --time=24:00:00  --mem-per-cpu 4000 my_job.sh # will probably require batching several times, depending on number of subjects
```


## Additional information

To have the generated template registered to an existing space (eg, ICBM152), please open an [issue](https://github.com/neuropoly/template/issues) and we will follow-up with you.


## Licence
This repository is under a MIT licence.
