"""
This script calls all the methods required for the data preprocessing.
The default dataset is an example dataset that is downloaded at the beginning of the script.
"""

from preprocessing import *

# downloading data and configuration file from OSF
path_data = download_data_template(path_data='./')

# extracting info from dataset
dataset_info = read_dataset(path_data + 'configuration.json', path_data=path_data)

# generating centerlines
list_centerline = generate_centerline(dataset_info=dataset_info, contrast='t1', regenerate=True)

# computing average template centerline and vertebral distribution
points_average_centerline, position_template_discs = average_centerline(list_centerline=list_centerline,
                                                                        dataset_info=dataset_info,
                                                                        use_ICBM152=False,
                                                                        use_label_ref='C1')

# generating the initial template space
generate_initial_template_space(dataset_info=dataset_info,
                                points_average_centerline=points_average_centerline,
                                position_template_discs=position_template_discs)

# straightening of all spinal cord
straighten_all_subjects(dataset_info=dataset_info, contrast='t1')

# normalize image intensity inside the spinal cord
normalize_intensity_template(dataset_info=dataset_info,
                             fname_template_centerline=dataset_info['path_template'] + 'template_centerline.npz',
                             contrast='t1',
                             verbose=1)

# copy preprocessed dataset in template folder
copy_preprocessed_images(dataset_info=dataset_info, contrast='t1')

# converting results to Minc format
convert_data2mnc(dataset_info, contrast='t1')
