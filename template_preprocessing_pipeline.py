"""
This script calls all the methods required for the data preprocessing.
The default dataset is an example dataset that is downloaded at the beginning of the script.
"""

from template_preprocessing import *
import sys

dataset_info = read_dataset(sys.argv[1])

# generating centerlines
list_centerline = generate_centerline(dataset_info = dataset_info, regenerate = True) 

# computing average template centerline and vertebral distribution
points_average_centerline, position_template_discs = average_centerline(list_centerline = list_centerline,
	dataset_info = dataset_info,
	use_ICBM152 = False,
	use_label_ref = 'C1')

# generating the initial template space
generate_initial_template_space(dataset_info = dataset_info,
	points_average_centerline = points_average_centerline,
	position_template_discs = position_template_discs)

# straightening of all spinal cord
straighten_all_subjects(dataset_info = dataset_info)

# normalize image intensity inside the spinal cord
normalize_intensity_template(dataset_info = dataset_info)

# copy preprocessed dataset in template folder
copy_preprocessed_images(dataset_info = dataset_info)

# converting results to Minc format
convert_data2mnc(dataset_info)
