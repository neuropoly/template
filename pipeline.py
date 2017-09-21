
from preprocessing import *

# downloading data and configuration file from OSF
path_data = download_data_template(path_data='./')

# extracting info from dataset
dataset_info = read_dataset(path_data + 'configuration.json', path_data=path_data)

# generating centerlines
list_centerline = generate_centerline(dataset_info=dataset_info, contrast='t1')

# computing average template centerline and vertebral distribution
points_average_centerline, position_template_disks = average_centerline(list_centerline=list_centerline,
                                                                        dataset_info=dataset_info)

# generating the initial template space
generate_initial_template_space(points_average_centerline=points_average_centerline,
                                position_template_disks=position_template_disks)

# straightening of all spinal cord
straighten_all_subjects(dataset_info=dataset_info, contrast='t1')

# converting results to Minc format
convert_data2mnc(dataset_info, contrast='t1')

