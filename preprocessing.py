import json
import os
import shutil
import numpy as np
import csv
from copy import copy
from tqdm import tqdm

from spinalcordtoolbox import utils as sct 
from spinalcordtoolbox.types import Centerline
from spinalcordtoolbox import straightening
from spinalcordtoolbox.centerline.core import ParamCenterline
from spinalcordtoolbox.centerline.core import get_centerline
from spinalcordtoolbox.image import Image
from spinalcordtoolbox.download import download_data, unzip

list_labels = [50, 49, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
               27, 28, 29, 30]
labels_regions = {'PMJ': 50, 'PMG': 49,
                  'C1': 1, 'C2': 2, 'C3': 3, 'C4': 4, 'C5': 5, 'C6': 6, 'C7': 7,
                  'T1': 8, 'T2': 9, 'T3': 10, 'T4': 11, 'T5': 12, 'T6': 13, 'T7': 14, 'T8': 15, 'T9': 16, 'T10': 17,
                  'T11': 18, 'T12': 19,
                  'L1': 20, 'L2': 21, 'L3': 22, 'L4': 23, 'L5': 24,
                  'S1': 25, 'S2': 26, 'S3': 27, 'S4': 28, 'S5': 29,
                  'Co': 30}
regions_labels = {'50': 'PMJ', '49': 'PMG',
                  '1': 'C1', '2': 'C2', '3': 'C3', '4': 'C4', '5': 'C5', '6': 'C6', '7': 'C7',
                  '8': 'T1', '9': 'T2', '10': 'T3', '11': 'T4', '12': 'T5', '13': 'T6', '14': 'T7', '15': 'T8',
                  '16': 'T9', '17': 'T10', '18': 'T11', '19': 'T12',
                  '20': 'L1', '21': 'L2', '22': 'L3', '23': 'L4', '24': 'L5',
                  '25': 'S1', '26': 'S2', '27': 'S3', '28': 'S4', '29': 'S5',
                  '30': 'Co'}
average_vert_length = {'PMJ': 30.0, 'PMG': 15.0, 'C1': 0.0,
                       'C2': 20.176514191661337, 'C3': 17.022090519403065, 'C4': 17.842111671016056,
                       'C5': 16.800356992319429, 'C6': 16.019212889311383, 'C7': 15.715854192723905,
                       'T1': 16.84466163681078, 'T2': 19.865049296865475, 'T3': 21.550165130933905,
                       'T4': 21.761237991438083, 'T5': 22.633281372803687, 'T6': 23.801974227738132,
                       'T7': 24.358357813758332, 'T8': 25.200266294477885, 'T9': 25.315272064638506,
                       'T10': 25.501856729317133, 'T11': 27.619238824308123, 'T12': 29.465119270009946,
                       'L1': 31.89272719870084, 'L2': 33.511890474486449, 'L3': 35.721413718617441}


def average_coordinates_over_slices(self, image): ### deprecated from latest version of spinalcordtoolbox
    # extracting points information for each coordinates
    P_x = np.array([point[0] for point in self.points])
    P_y = np.array([point[1] for point in self.points])
    P_z = np.array([point[2] for point in self.points])
    P_z_vox = np.array([coord[2] for coord in image.transfo_phys2pix(self.points)])
    P_x_d = np.array([deriv[0] for deriv in self.derivatives])
    P_y_d = np.array([deriv[1] for deriv in self.derivatives])
    P_z_d = np.array([deriv[2] for deriv in self.derivatives])

    P_z_vox = np.array([int(np.round(P_z_vox[i])) for i in range(0, len(P_z_vox))])
    # not perfect but works (if "enough" points), in order to deal with missing z slices
    for i in range(min(P_z_vox), max(P_z_vox) + 1, 1):
        if i not in P_z_vox:
            from bisect import bisect_right
            idx_closest = bisect_right(P_z_vox, i)
            z_min, z_max = P_z_vox[idx_closest - 1], P_z_vox[idx_closest]
            if z_min == z_max:
                weight_min = weight_max = 0.5
            else:
                weight_min, weight_max = abs((z_min - i) / (z_max - z_min)), abs((z_max - i) / (z_max - z_min))
            P_x_temp = np.insert(P_x, idx_closest, weight_min * P_x[idx_closest - 1] + weight_max * P_x[idx_closest])
            P_y_temp = np.insert(P_y, idx_closest, weight_min * P_y[idx_closest - 1] + weight_max * P_y[idx_closest])
            P_z_temp = np.insert(P_z, idx_closest, weight_min * P_z[idx_closest - 1] + weight_max * P_z[idx_closest])
            P_x_d_temp = np.insert(P_x_d, idx_closest, weight_min * P_x_d[idx_closest - 1] + weight_max * P_x_d[idx_closest])
            P_y_d_temp = np.insert(P_y_d, idx_closest, weight_min * P_y_d[idx_closest - 1] + weight_max * P_y_d[idx_closest])
            P_z_d_temp = np.insert(P_z_d, idx_closest, weight_min * P_z_d[idx_closest - 1] + weight_max * P_z_d[idx_closest])
            P_z_vox_temp = np.insert(P_z_vox, idx_closest, i)
            P_x, P_y, P_z, P_x_d, P_y_d, P_z_d, P_z_vox = P_x_temp, P_y_temp, P_z_temp, P_x_d_temp, P_y_d_temp, P_z_d_temp, P_z_vox_temp

    coord_mean = np.array([[np.mean(P_x[P_z_vox == i]), np.mean(P_y[P_z_vox == i]), np.mean(P_z[P_z_vox == i])] for i in range(min(P_z_vox), max(P_z_vox) + 1, 1)])
    x_centerline_fit = coord_mean[:, :][:, 0]
    y_centerline_fit = coord_mean[:, :][:, 1]
    coord_mean_d = np.array([[np.mean(P_x_d[P_z_vox == i]), np.mean(P_y_d[P_z_vox == i]), np.mean(P_z_d[P_z_vox == i])] for i in range(min(P_z_vox), max(P_z_vox) + 1, 1)])
    z_centerline = coord_mean[:, :][:, 2]
    x_centerline_deriv = coord_mean_d[:, :][:, 0]
    y_centerline_deriv = coord_mean_d[:, :][:, 1]
    z_centerline_deriv = coord_mean_d[:, :][:, 2]

    return x_centerline_fit, y_centerline_fit, z_centerline, x_centerline_deriv, y_centerline_deriv, z_centerline_deriv

###### DELETE BELOW: 
# def _get_coordinate_interpolated(self, vertebral_level, relative_position, backup_index = None, backup_centerline = None, mode = 'levels'):
#     index_closest = self.get_closest_to_absolute_position(vertebral_level, relative_position, backup_index = backup_index, backup_centerline = backup_centerline)
#     if index_closest is None:
#         return [np.nan, np.nan, np.nan]

#     relative_position_closest = self.dist_points_rel[index_closest]
#     coordinate_closest = self.points[index_closest]

#     if relative_position < relative_position_closest:
#         index_next = index_closest + 1
#     else:
#         index_next = index_closest - 1
#     relative_position_next = self.dist_points_rel[index_next]
#     coordinate_next = self.points[index_next]
#     #if (relative_position_next != relative_position_closest):
#     weight_closest = abs(relative_position - relative_position_closest) / abs(relative_position_next - relative_position_closest)
#     weight_next = abs(relative_position - relative_position_next) / abs(relative_position_next - relative_position_closest)
#     #else:
#        # weight_closest = 1
#        # weight_next = 0 # same thing!
#     coordinate_result = [weight_closest * coordinate_closest[0] + weight_next * coordinate_next[0],
#                          weight_closest * coordinate_closest[1] + weight_next * coordinate_next[1],
#                          weight_closest * coordinate_closest[2] + weight_next * coordinate_next[2]]

#     return coordinate_result

def get_lowest_vert_dataset(dataset_info): ### NEW + FIX
    """
    This function generates spinal cord centerline from binary images (either an image of centerline or segmentation)
    :param dataset_info: dictionary containing dataset information
    :param contrast: {'t1', 't2'}
    :return list of centerline objects
    """
    path_data = dataset_info['path_data']
    path_derivatives = path_data + 'derivatives'
    list_subjects = dataset_info['subjects'].split(', ') 
    lowest_vert = 100

    for subject_name in list_subjects:
        fname_centerline = path_derivatives + '/' + dataset_info['pipeline_centerline'] + '/' + subject_name +  '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_centerline']
        if os.path.isfile(fname_centerline + '.npz'):               
            centerline = Centerline(fname = fname_centerline + '.npz')
            dist_C1_dict = {}
            tmp_list = []
            for key,value in centerline.distance_from_C1label.items(): 
                if value in tmp_list: continue
                else:
                    tmp_list.append(value)
                    dist_C1_dict[key] = value
            if len(dist_C1_dict) < lowest_vert: lowest_vert = len(dist_C1_dict)
        else:
            print("Centerline for " + subject_name + " does not exist!")
    return(lowest_vert)

def read_dataset(fname_json = 'configuration.json', path_data = './'): ### TO COMPLETE
    """
    This function reads a json file that describes the dataset, including the list of subjects as well as
    suffix for filenames (centerline, discs, segmentations, etc.).
    The function raises an exception if the file is missing or if required fields are missing from the json file.
    :param fname_json: path + file name to json description file.
    :return: a dictionary with all the fields contained in the json file.
    """
    if not os.path.isfile(fname_json):
        raise ValueError('File ' + fname_json + ' doesn\'t seem to exist. Please check your data.')

    with open(fname_json) as data_file:
        dataset_info = json.load(data_file)

    error = ''
    key_list = ["path_data", "subjects", "data_type", "contrast", "suffix_image", "suffix_label-SC_seg", "suffix_label-disc"]
    for key in key_list:
        if key not in dataset_info.keys(): error += 'Dataset configuration file ' + fname_json + ' must contain the field ' + key + '.\n'

    # check if path to data and template exist and are absolute
    if 'path_data' in dataset_info and not os.path.isdir(dataset_info['path_data']): error += 'Path to data (field \'path_data\') must exist.\n'

    # if there are some errors, raise an exception
    if error != '': raise ValueError('JSON file containing dataset info is incomplete:\n' + error)

    return dataset_info

def generate_centerline(dataset_info, lowest_disc = 25, contrast = 't1', regenerate = False, algo_fitting = 'linear', smooth = 50, degree = None, minmax = None):
    """
    This function generates spinal cord centerline from binary images (either an image of centerline or segmentation)
    :param dataset_info: dictionary containing dataset information
    :param contrast: {'t1', 't2'}
    :return list of centerline objects
    """
    contrast = dataset_info['contrast']
    path_data = dataset_info['path_data']
    list_subjects = dataset_info['subjects'].split(', ') 
    list_centerline = []
    current_path = os.getcwd()

    tqdm_bar = tqdm(total = len(list_subjects), unit = 'B', unit_scale = True, desc = "Status", ascii = True)

    # obtaining centerline of each subject
    for subject_name in list_subjects:
        fname_image = path_data + subject_name + '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '.nii.gz'
        fname_image_seg = path_data + 'derivatives/labels/' + subject_name +  '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_label-SC_seg'] + '.nii.gz'
        fname_discs = path_data + 'derivatives/labels/' + subject_name +  '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_label-disc']
        fname_image_discs = fname_discs + '-manual.nii.gz' if os.path.isfile(fname_discs + '-manual.nii.gz') else fname_discs + '.nii.gz'
        fname_centerline = path_data + 'derivatives/labels/' + subject_name +  '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '_label-centerline'

        # if centerline exists, we load it, if not, we compute it
        if os.path.isfile(fname_centerline + '.npz') and not regenerate:
            print("Centerline for " + subject_name + " exists and will not be recomputed!")
            centerline = Centerline(fname = fname_centerline + '.npz')
        else:
            if os.path.isfile(fname_image_seg):
                print(subject_name + ' SC segmentation exists. Extracting centerline from ' + fname_image_seg)
                im_seg = Image(fname_image_seg).change_orientation('RPI')
                param_centerline = ParamCenterline(algo_fitting = algo_fitting, contrast = contrast, smooth = smooth, degree = degree, minmax = minmax) 
            else:
                print(subject_name + ' SC segmentation does not exist. Extracting centerline from ' + fname_image)
                im_seg = Image(fname_image).change_orientation('RPI')
                param_centerline = ParamCenterline(algo_fitting = 'optic', contrast = contrast, smooth = smooth, degree = 5, minmax = minmax)

            # extracting intervertebral discs
            im_discs = Image(fname_image_discs).change_orientation('RPI')
            coord = im_discs.getNonZeroCoordinates(sorting = 'z', reverse_coord = True)
            coord_physical = []
            for c in coord:
                if c.value <= lowest_disc or c.value in [48, 49, 50, 51, 52]:
                    c_p = list(im_discs.transfo_pix2phys([[c.x, c.y, c.z]])[0])
                    c_p.append(c.value)
                    coord_physical.append(c_p)

            # extracting centerline
            im_ctl, arr_ctl, arr_ctl_der, _ = get_centerline(im_seg, param = param_centerline, space = 'phys')

            # save centerline as .nii.gz file
            im_ctl.save(fname_centerline + '.nii.gz', dtype = 'float32')
            centerline = Centerline(points_x = arr_ctl[0], points_y = arr_ctl[1], points_z = arr_ctl[2], deriv_x = arr_ctl_der[0], deriv_y = arr_ctl_der[1], deriv_z = arr_ctl_der[2])
            centerline.compute_vertebral_distribution(coord_physical)
            # save centerline .npz file
            centerline.save_centerline(fname_output = fname_centerline)

        list_centerline.append(centerline)
        tqdm_bar.update(1)
    tqdm_bar.close()
    os.chdir(current_path)
    return list_centerline

# def compute_ICBM152_centerline(dataset_info): ###### FIX
#     """
#     This function extracts the centerline from the ICBM152 brain template
#     :param dataset_info: dictionary containing dataset information
#     :return:
#     """
#     path_data = dataset_info['path_data']

#     if not os.path.isdir(path_data + 'icbm152/'):
#         download_data_template(path_data = path_data, name = 'icbm152', force = False)

#     image_discs = Image(path_data + 'icbm152/mni_icbm152_t1_tal_nlin_sym_09c_discs_manual.nii.gz')
#     coord = image_discs.getNonZeroCoordinates(sorting = 'z', reverse_coord = True)
#     coord_physical = []

#     for c in coord:
#         if c.value <= 20 or c.value in [48, 49, 50, 51, 52]:  # 22 corresponds to L2
#             c_p = list(image_discs.transfo_pix2phys([[c.x, c.y, c.z]])[0])
#             c_p.append(c.value)
#             coord_physical.append(c_p)

#     x_centerline_fit, y_centerline_fit, z_centerline, x_centerline_deriv, y_centerline_deriv, z_centerline_deriv = smooth_centerline(
#         path_data + 'icbm152/mni_icbm152_t1_centerline_manual.nii.gz', algo_fitting = 'nurbs',
#         verbose = 0, nurbs_pts_number = 300, all_slices = False, phys_coordinates = True, remove_outliers = False)

#     centerline = Centerline(x_centerline_fit, y_centerline_fit, z_centerline, x_centerline_deriv, y_centerline_deriv, z_centerline_deriv)

#     centerline.compute_vertebral_distribution(coord_physical, label_reference = 'PMG')
#     return centerline

def average_centerline(list_centerline, dataset_info, use_ICBM152 = False, use_label_ref = None, lowest_disc_quantile = 0.75):
    """
    This function compute the average centerline and vertebral distribution, that will be used to create the
    final template space.
    :param list_centerline: list of Centerline objects, for all subjects
    :param dataset_info: dictionary containing dataset information
    :return: points_average_centerline: list of points (x, y, z) of the average spinal cord and brainstem centerline
             position_template_discs: index of intervertebral discs along the template centerline
    """

    # extracting centerline from ICBM152
    # if use_ICBM152: centerline_icbm152 = compute_ICBM152_centerline(dataset_info) ###### FIX
    
    list_dist_discs = []
    for centerline in list_centerline: list_dist_discs.append(centerline.distance_from_C1label)

    # finding lowest disc of the template, according to the dataset being used
    list_lowest_disc = []
    for val in list_dist_discs: list_lowest_disc.append(len(val))
    lowest_disc =  int(np.quantile((np.array(list_lowest_disc)), lowest_disc_quantile))

    # generating custom list of average vertebral lengths
    new_vert_length = {}
    for dist_discs in list_dist_discs:
        for i, disc_label in enumerate(dist_discs):
            if i < lowest_disc:
                if disc_label == 'PMJ':
                    length = abs(dist_discs[disc_label] - dist_discs['PMG'])
                elif disc_label == 'PMG':
                    length = abs(dist_discs[disc_label] - dist_discs['C1'])
                else:
                    index_current_label = list_labels.index(labels_regions[disc_label])
                    next_label = regions_labels[str(list_labels[index_current_label + 1])]
                    if next_label in dist_discs:
                        length = abs(dist_discs[disc_label] - dist_discs[next_label])
                        if disc_label in new_vert_length:
                            new_vert_length[disc_label].append(length)
                        else:
                            new_vert_length[disc_label] = [length]
    new_average_vert_length = {}
    for disc_label in new_vert_length: new_average_vert_length[disc_label] = np.mean(new_vert_length[disc_label])

    # computing length of each vertebral level
    length_vertebral_levels = {}
    for dist_discs in list_dist_discs:
        for disc_label in new_vert_length:
            if disc_label in dist_discs: 
                if disc_label == 'PMJ':
                    length = abs(dist_discs[disc_label] - dist_discs['PMG'])
                elif disc_label == 'PMG':
                    length = abs(dist_discs[disc_label] - dist_discs['C1'])
                else:
                    index_current_label = list_labels.index(labels_regions[disc_label])
                    next_label = regions_labels[str(list_labels[index_current_label + 1])]
                    if next_label in dist_discs:
                        length = abs(dist_discs[disc_label] - dist_discs[next_label])
                    else:
                        length = new_average_vert_length[disc_label]
            else: length = new_average_vert_length[disc_label]

            if disc_label in length_vertebral_levels:
                length_vertebral_levels[disc_label].append(length)
            else:
                length_vertebral_levels[disc_label] = [length]
    
    # averaging the length of vertebral levels
    average_length = {}
    for disc_label in length_vertebral_levels:
        mean = np.mean(length_vertebral_levels[disc_label])
        std = np.std(length_vertebral_levels[disc_label])
        average_length[disc_label] = [disc_label, mean, std]

    # computing distances of discs from C1, based on average length
    distances_discs_from_C1 = {'C1': 0.0}
    if 'PMG' in average_length:
        distances_discs_from_C1['PMG'] = -average_length['PMG'][1]
        if 'PMJ' in average_length:
            distances_discs_from_C1['PMJ'] = -average_length['PMG'][1] - average_length['PMJ'][1]
    for disc_number in list_labels:
        if disc_number not in [50, 49, 1] and regions_labels[str(disc_number)] in average_length:
            distances_discs_from_C1[regions_labels[str(disc_number)]] = distances_discs_from_C1[regions_labels[str(disc_number - 1)]] + average_length[regions_labels[str(disc_number)]][1]

    # calculating discs average distances from C1
    average_distances = []
    for disc_label in distances_discs_from_C1:
        mean = np.mean(distances_discs_from_C1[disc_label])
        std = np.std(distances_discs_from_C1[disc_label])
        average_distances.append([disc_label, mean, std])

    # averaging distances for all subjects and calculating relative positions
    average_distances = sorted(average_distances, key = lambda x: x[1], reverse = False)
    number_of_points_between_levels = 100
    disc_average_coordinates = {}
    points_average_centerline = []
    label_points = []
    average_positions_from_C1 = {}
    disc_position_in_centerline = {}

    # iterate over each disc level
    for i in range(len(average_distances)): ###### C1, C2, C3, C4, ...
        disc_label = average_distances[i][0]
        average_positions_from_C1[disc_label] = average_distances[i][1]

        for j in range(number_of_points_between_levels): ###### C1: {0, 1, 2, 3, ...}
            relative_position = float(j) / float(number_of_points_between_levels) ###### C1: {0/100, 1/100, 2/100, 3/100, ...}
            if disc_label in ['PMJ', 'PMG']:
                relative_position = 1.0 - relative_position
            list_coordinates = [[]] * len(list_centerline)
            for k, centerline in enumerate(list_centerline): ###### iterate through each centerline and get actual absolute coordinate
                #if disc_label in centerline.distance_from_C1label:
               list_coordinates[k] = centerline.get_closest_to_relative_position(disc_label, relative_position) ### centerline.get_coordinate_interpolated(disc_label, relative_position)
            # average all coordinates
            get_avg = []
            for item in list_coordinates: 
                if item != None: get_avg.append(item)
            average_coord = np.array(get_avg).mean()
            # add it to averaged centerline list of points
            points_average_centerline.append(average_coord)
            label_points.append(disc_label)
            if j == 0:
                disc_average_coordinates[disc_label] = average_coord
                disc_position_in_centerline[disc_label] = i * number_of_points_between_levels
    
    # create final template space
    if use_label_ref is not None:
        label_ref = use_label_ref
        if label_ref not in length_vertebral_levels:
            raise Exception('ERROR: the reference label passed in argument ' + label_ref + ' should be present in the images.')
    else:
        if 'PMG' in length_vertebral_levels:
            label_ref = 'PMG'
        elif 'C1' in length_vertebral_levels:
            label_ref = 'C1'
        else:
            raise Exception('ERROR: the images should always have C1 label.')

    position_template_discs = {}

    if use_ICBM152:
        coord_ref = np.copy(centerline_icbm152.points[centerline_icbm152.index_disc[label_ref]])
        for disc in average_length:
            if disc in ['C1', 'PMJ', 'PMG']:
                position_template_discs[disc] = centerline_icbm152.points[centerline_icbm152.index_disc[disc]]
            else:
                coord_disc = coord_ref.copy()
                coord_disc[2] -= average_positions_from_C1[disc] - average_positions_from_C1[label_ref]
                position_template_discs[disc] = coord_disc
    else:
        coord_ref = np.array([0.0, 0.0, 0.0])
        for disc in average_length:
            coord_disc = coord_ref.copy()
            coord_disc[2] -= average_positions_from_C1[disc] - average_positions_from_C1[label_ref]
            position_template_discs[disc] = coord_disc

    # change centerline to be straight below reference if using ICBM152
    if use_ICBM152:
        index_straight = disc_position_in_centerline[label_ref]
    else:  # else: straighten every points along centerline
        index_straight = 0

    points_average_centerline_template = []
    for i in range(0, len(points_average_centerline)):
        current_label = label_points[i]
        if current_label in average_length:
            length_current_label = average_length[current_label][1]
            relative_position_from_disc = float(i - disc_position_in_centerline[current_label]) / float(number_of_points_between_levels)
            temp_point = np.copy(coord_ref)

            if i >= index_straight:
                index_current_label = list_labels.index(labels_regions[current_label])
                next_label = regions_labels[str(list_labels[index_current_label + 1])]
                if next_label not in average_positions_from_C1:
                    temp_point[2] = coord_ref[2] - average_positions_from_C1[current_label] - relative_position_from_disc * length_current_label
                else:
                    temp_point[2] = coord_ref[2] - average_positions_from_C1[current_label] - abs(relative_position_from_disc * (average_positions_from_C1[current_label] - average_positions_from_C1[next_label]))
            points_average_centerline_template.append(temp_point)

    if use_ICBM152:
        # append ICBM152 centerline from PMG
        points_icbm152 = centerline_icbm152.points[centerline_icbm152.index_disc[label_ref]:]
        points_icbm152 = points_icbm152[::-1]
        points_average_centerline = np.concatenate([points_icbm152, points_average_centerline_template])
    else:
        points_average_centerline = points_average_centerline_template
    return points_average_centerline, position_template_discs

def generate_initial_template_space(dataset_info, points_average_centerline, position_template_discs, contrast = 't1', algo_fitting = 'linear', smooth = 50, degree = None, minmax = None): ##DONE additional options in nb/generate_initial_template_space_branch
    """
    This function generates the initial template space, on which all images will be registered.
    :param points_average_centerline: list of points (x, y, z) of the average spinal cord and brainstem centerline
    :param position_template_discs: index of intervertebral discs along the template centerline
    :return: NIFTI files in RPI orientation (template space, template centerline, template disc positions) & .npz file of template Centerline object ##DONE package updates in nb/generate_initial_template_space_branch
    """
    # initializing variables
    contrast = dataset_info['contrast']
    path_template = dataset_info['path_data'] + 'derivatives/template/'
    if not os.path.exists(path_template): os.makedirs(path_template)

    x_size_of_template_space, y_size_of_template_space = 201, 201
    spacing = 0.5

    # creating template space
    size_template_z = int(abs(points_average_centerline[0][2] - points_average_centerline[-1][2]) / spacing) + 15
    template_space = Image([x_size_of_template_space, y_size_of_template_space, size_template_z])
    template_space.data = np.zeros((x_size_of_template_space, y_size_of_template_space, size_template_z))
    template_space.hdr.set_data_dtype('float32')
    origin = [points_average_centerline[-1][0] + x_size_of_template_space * spacing / 2.0,
              points_average_centerline[-1][1] - y_size_of_template_space * spacing / 2.0,
              (points_average_centerline[-1][2] - spacing)]
    template_space.hdr.as_analyze_map()['dim'] = [3.0, x_size_of_template_space, y_size_of_template_space, size_template_z, 1.0, 1.0, 1.0, 1.0]
    template_space.hdr.as_analyze_map()['qoffset_x'] = origin[0]
    template_space.hdr.as_analyze_map()['qoffset_y'] = origin[1]
    template_space.hdr.as_analyze_map()['qoffset_z'] = origin[2]
    template_space.hdr.as_analyze_map()['srow_x'][-1] = origin[0]
    template_space.hdr.as_analyze_map()['srow_y'][-1] = origin[1]
    template_space.hdr.as_analyze_map()['srow_z'][-1] = origin[2]
    template_space.hdr.as_analyze_map()['srow_x'][0] = -spacing
    template_space.hdr.as_analyze_map()['srow_y'][1] = spacing
    template_space.hdr.as_analyze_map()['srow_z'][2] = spacing
    template_space.hdr.set_sform(template_space.hdr.get_sform())
    template_space.hdr.set_qform(template_space.hdr.get_sform())
    template_space.save(path_template + 'template_space.nii.gz', dtype = 'uint8')
    print(f'\nSaving template space in {template_space.orientation} orientation as {path_template}template_space.nii.gz\n')

    # generate template centerline as an image
    image_centerline = template_space.copy()
    for coord in points_average_centerline:
        coord_pix = image_centerline.transfo_phys2pix([coord])[0]
        if 0 <= coord_pix[0] < image_centerline.data.shape[0] and 0 <= coord_pix[1] < image_centerline.data.shape[1] and 0 <= coord_pix[2] < image_centerline.data.shape[2]:
            image_centerline.data[int(coord_pix[0]), int(coord_pix[1]), int(coord_pix[2])] = 1
    image_centerline.save(path_template + 'template_label-centerline.nii.gz', dtype = 'float32')
    print(f'\nSaving template centerline in {template_space.orientation} orientation as {path_template}template_label-centerline.nii.gz\n')

    # generate template discs position
    coord_physical = []
    image_discs = template_space.copy()
    for disc in position_template_discs:
        label = labels_regions[disc]
        coord = position_template_discs[disc]
        coord_pix = image_discs.transfo_phys2pix([coord])[0]

        coord = coord.tolist()
        coord.append(label)
        coord_physical.append(coord)
        if 0 <= coord_pix[0] < image_discs.data.shape[0] and 0 <= coord_pix[1] < image_discs.data.shape[1] and 0 <= coord_pix[2] < image_discs.data.shape[2]:
            image_discs.data[int(coord_pix[0]), int(coord_pix[1]), int(coord_pix[2])] = label
        else:
            sct.printv(str(coord_pix))
            sct.printv('ERROR: the disc label ' + str(disc) + ' is not in the template image.')
    image_discs.save(path_template + 'template_label-disc.nii.gz', dtype = 'uint8')
    print(f'\nSaving disc positions in {image_discs.orientation} orientation as {path_template}template_label-disc.nii.gz\n') ###NEW

    # generate template centerline as a npz file ##DONE updated template Centerline object creation and saving as .npz file in nb/generate_initial_template_space_branch
    param_centerline = ParamCenterline(algo_fitting = algo_fitting, contrast = contrast, smooth = smooth, degree = degree, minmax = minmax) 
    # centerline params of original template centerline had options that you cannot just provide `get_centerline` with anymroe (algo_fitting = 'nurbs', nurbs_pts_number = 4000, all_slices = False, phys_coordinates = True, remove_outliers = True)
    _, arr_ctl, arr_ctl_der, _ = get_centerline(image_centerline, param = param_centerline, space = 'phys') ### we don't need to save im_centerline! ### straightening._get_centerline(im_seg,param_centerline, 1) ### What Rohan & Benjamin added!
    centerline_template = Centerline(points_x = arr_ctl[0], points_y = arr_ctl[1], points_z = arr_ctl[2], deriv_x = arr_ctl_der[0], deriv_y = arr_ctl_der[1], deriv_z = arr_ctl_der[2])
    centerline_template.compute_vertebral_distribution(coord_physical)        
    centerline_template.save_centerline(fname_output = path_template + 'template_label-centerline')
    print(f'\nSaving template centerline as .npz file (saves all Centerline object information, not just coordinates) as {path_template}template_label-centerline.npz\n')

def straighten_all_subjects(dataset_info, normalized = False, contrast = 't1'): ### NOTE: outputs this to "BIDS" dir for this!
    """
    This function straighten all images based on template centerline
    :param dataset_info: dictionary containing dataset information
    :param normalized: True if images were normalized before straightening
    :param contrast: {'t1', 't2'}
    """
    contrast = dataset_info['contrast']
    path_data = dataset_info['path_data']
    path_template = dataset_info['path_data'] + 'derivatives/template/'
    list_subjects = dataset_info['subjects'].split(', ')

    if not os.path.exists(dataset_info['path_data'] + 'derivatives/sct_straighten_spinalcord'): os.makedirs(dataset_info['path_data'] + 'derivatives/sct_straighten_spinalcord')

    # straightening of each subject on the new template
    tqdm_bar = tqdm(total = len(list_subjects), unit = 'B', unit_scale = True, desc = "Status", ascii = True)
    for subject_name in list_subjects:
        folder_out = dataset_info['path_data'] + 'derivatives/sct_straighten_spinalcord/' + subject_name + '/' + dataset_info['data_type']
        if not os.path.exists(folder_out): os.makedirs(folder_out)
        
        fname_image = path_data + subject_name + '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '.nii.gz'
        fname_image_seg = path_data + 'derivatives/labels/' + subject_name +  '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_label-SC_seg'] + '.nii.gz'
        fname_discs = path_data + 'derivatives/labels/' + subject_name +  '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_label-disc']
        fname_image_discs = fname_discs + '-manual.nii.gz' if os.path.isfile(fname_discs + '-manual.nii.gz') else fname_discs + '.nii.gz'
        fname_image_centerline = path_data + 'derivatives/labels/' + subject_name +  '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '_label-centerline.nii.gz'
        fname_out = subject_name + dataset_info['suffix_image'] + '_straight_norm.nii.gz' if normalized else subject_name + dataset_info['suffix_image'] + '_straight.nii.gz' 

        fname_input_seg = fname_image_seg if os.path.isfile(fname_image_seg) else fname_image_centerline
        # go to output folder
        sct.printv('\nStraightening ' + fname_image)
        os.chdir(folder_out)
 
        # straighten centerline
        os.system('sct_straighten_spinalcord' + 
            ' -i ' + fname_image + 
            ' -s ' + fname_input_seg + 
            ' -dest ' + path_template + 'template_label-centerline.nii.gz' + 
            ' -ldisc-input ' + fname_image_discs +        
            ' -ldisc-dest ' + path_template + 'template_label-disc.nii.gz' + 
            ' -ofolder ' + folder_out + 
            ' -o ' + fname_out + 
            ' -disable-straight2curved' + 
            ' -param threshold_distance=1')
        tqdm_bar.update(1)
    tqdm_bar.close()

def normalize_intensity_template(dataset_info, contrast = 't1', verbose = 1): ### Removed fname_template_centerline = None -> why would we want this?
    """
    This function normalizes the intensity of the image inside the spinal cord
    :return:
    """
    contrast = dataset_info['contrast']
    fname_template_centerline = dataset_info['path_data'] + 'derivatives/template/' + 'template_label-centerline.npz'
    list_subjects = dataset_info['subjects'].split(', ') ###NEW

    average_intensity = []
    intensity_profiles = {}
    

    tqdm_bar = tqdm(total = len(list_subjects), unit = 'B', unit_scale = True, desc = "Status", ascii = True)

    # computing the intensity profile for each subject
    for subject_name in list_subjects:
        fname_image = dataset_info['path_data'] + 'derivatives/sct_straighten_spinalcord/' + subject_name + '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '_straight.nii.gz'
        centerline_template = Centerline(fname = fname_template_centerline)
        image = Image(fname_image)
        nx, ny, nz, nt, px, py, pz, pt = image.dim
        x, y, z, xd, yd, zd = average_coordinates_over_slices(self = centerline_template, image = image)


        # Compute intensity values
        z_values, intensities = [], []
        extend = 1  # this means the mean intensity of the slice will be calculated over a 3x3 square
        for i in range(len(z)):
            coord_z = image.transfo_phys2pix([[x[i], y[i], z[i]]])[0]
            z_values.append(coord_z[2])
            intensities.append(np.mean(image.data[coord_z[0] - extend - 1:coord_z[0] + extend, coord_z[1] - extend - 1:coord_z[1] + extend, coord_z[2]]))

        # for the slices that are not in the image, extend min and max values to cover the whole image
        min_z, max_z = min(z_values), max(z_values)
        intensities_temp = copy(intensities)
        z_values_temp = copy(z_values)
        for cz in range(nz):
            if cz not in z_values:
                z_values_temp.append(cz)
                if cz < min_z:
                    intensities_temp.append(intensities[z_values.index(min_z)])
                elif cz > max_z:
                    intensities_temp.append(intensities[z_values.index(max_z)])
                else:
                    print ('error...', cz)
        intensities = intensities_temp
        z_values = z_values_temp

        # Preparing data for smoothing
        arr_int = [[z_values[i], intensities[i]] for i in range(len(z_values))]
        arr_int.sort(key = lambda x: x[0])  # and make sure it is ordered with z
        
        def smooth(x, window_len = 11, window = 'hanning'):
            """smooth the data using a window with requested size.
            """
           
            if x.ndim != 1:
                raise ValueError("smooth only accepts 1 dimension arrays.")

            if x.size < window_len:
                raise ValueError("Input vector needs to be bigger than window size.")

            if window_len < 3:
                return x

            if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
                raise ValueError("Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")

            s = np.r_[x[window_len - 1:0:-1], x, x[-2:-window_len - 1:-1]]
            if window == 'flat':  # moving average
                w = np.ones(window_len, 'd')
            else:
                w = eval('np.' + window + '(window_len)')

            y = np.convolve(w / w.sum(), s, mode = 'same')
            return y[window_len - 1:-window_len + 1]
          

        # Smoothing
        intensities = [c[1] for c in arr_int]
        intensity_profile_smooth = smooth(np.array(intensities), window_len = 50)
        average_intensity.append(np.mean(intensity_profile_smooth))

        intensity_profiles[subject_name] = intensity_profile_smooth

        if verbose == 2:
            import matplotlib.pyplot as plt
            plt.figure()
            plt.title(subject_name)
            plt.plot(intensities)
            plt.plot(intensity_profile_smooth)
            plt.show()

    # set the average image intensity over the entire dataset
    average_intensity = 1000.0

    # normalize the intensity of the image based on spinal cord
    for subject_name in list_subjects:
        fname_image = dataset_info['path_data'] + 'derivatives/sct_straighten_spinalcord/' + subject_name + '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '_straight.nii.gz'
        fname_image_normalized = dataset_info['path_data'] + 'derivatives/sct_straighten_spinalcord/' + subject_name + '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '_straight_norm.nii.gz'
        image = Image(fname_image)
        nx, ny, nz, nt, px, py, pz, pt = image.dim

        image_new = image.copy()
        image_new.change_type(dtype = 'float32')
        for i in range(nz):
            if intensity_profiles[subject_name][i] == 0: intensity_profiles[subject_name][i] = 0.001 ### is this how Rohan solved this?
            image_new.data[:, :, i] *= average_intensity / intensity_profiles[subject_name][i]

        # Save intensity normalized template
        image_new.save(fname_image_normalized)

def copy_preprocessed_images(dataset_info, contrast = 't1'):
    contrast = dataset_info['contrast']
    list_subjects = dataset_info['subjects'].split(', ') 
    
    tqdm_bar = tqdm(total = len(list_subjects), unit = 'B', unit_scale = True, desc = "Status", ascii = True)
    
    for subject_name in list_subjects:
        fname_image = dataset_info['path_data'] + 'derivatives/sct_straighten_spinalcord/' + subject_name + '/' + dataset_info['data_type'] + '/' + subject_name + dataset_info['suffix_image'] + '_straight_norm.nii.gz'
        shutil.copy(fname_image, dataset_info['path_data'] + 'derivatives/template/' + subject_name + dataset_info['suffix_image'] + '_straight_norm.nii.gz')
        tqdm_bar.update(1)
    tqdm_bar.close()

def create_mask_template(dataset_info, contrast = 't1'):
    path_template = dataset_info['path_data'] + 'derivatives/template/'
    subject_name = dataset_info['subjects'].split(', ')[0]

    template_mask = Image(path_template + subject_name + dataset_info['suffix_image'] + '_straight_norm.nii.gz')
    template_mask.data *= 0.0
    template_mask.data += 1.0
    template_mask.save(path_template + '/template_mask.nii.gz')

    # if mask already present, deleting it
    if os.path.isfile(path_template + '/template_mask.mnc'): os.remove(path_template + '/template_mask.mnc')

    os.system('nii2mnc ' + path_template + '/template_mask.nii.gz ' + ' ' + path_template + '/template_mask.mnc')
    return path_template + '/template_mask.mnc'

def convert_data2mnc(dataset_info, contrast = 't1'):
    contrast = dataset_info['contrast']
    path_template = dataset_info['path_data'] + 'derivatives/template/'
    list_subjects = dataset_info['subjects'].split(', ')

    path_template_mask = create_mask_template(dataset_info, contrast)

    output_list = open('subjects.csv', "w")
    writer = csv.writer(output_list, delimiter = ',', quotechar = ',', quoting = csv.QUOTE_MINIMAL)

    tqdm_bar = tqdm(total = len(list_subjects), unit = 'B', unit_scale = True, desc = "Status", ascii = True)
    for subject_name in list_subjects:
        fname_nii = path_template + subject_name + dataset_info['suffix_image'] + '_straight_norm.nii.gz'
        fname_mnc = path_template + subject_name + dataset_info['suffix_image'] + '_straight_norm.mnc'

        # if file already present, deleting it
        if os.path.isfile(fname_mnc): os.remove(fname_mnc)

        os.system('nii2mnc ' + fname_nii + ' ' + fname_mnc)
        os.remove(fname_nii) # remove duplicate nifti file!

        writer.writerow([fname_mnc,path_template_mask])

        tqdm_bar.update(1)
    tqdm_bar.close()

    output_list.close()

