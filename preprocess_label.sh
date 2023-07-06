#!/bin/bash

sct_run_batch -jobs 6 -path-data "/PATH/TO/dataset" \
        -subject-prefix "sub-" -exclude-list sub-107 sub-125 -script segment_subjects.sh \
	-path-output "/PATH/TO/dataset/derivatives/labels"

