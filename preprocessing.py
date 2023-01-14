import json
import os
import shutil
import numpy as np
import csv
from copy import copy
from tqdm import tqdm
import gzip 
import nibabel as nib

from spinalcordtoolbox import *
from spinalcordtoolbox import straightening
from spinalcordtoolbox import utils as sct
from spinalcordtoolbox.types import Centerline
from spinalcordtoolbox.centerline.core import *
from spinalcordtoolbox.download import download_data, unzip
from spinalcordtoolbox.image import Image

labels_regions = {'C1': 1, 'C2': 2, 'C3': 3, 'C4': 4, 'C5': 5, 'C6': 6, 'C7': 7,
                  'T1': 8, 'T2': 9, 'T3': 10, 'T4': 11, 'T5': 12, 'T6': 13, 'T7': 14, 'T8': 15, 'T9': 16, 'T10': 17,
                  'T11': 18, 'T12': 19,
                  'L1': 20, 'L2': 21, 'L3': 22, 'L4': 23, 'L5': 24,
                  'S1': 25, 'S2': 26}

regions_labels = {'1': 'C1', '2': 'C2', '3': 'C3', '4': 'C4', '5': 'C5', '6': 'C6', '7': 'C7',
                  '8': 'T1', '9': 'T2', '10': 'T3', '11': 'T4', '12': 'T5', '13': 'T6', '14': 'T7', '15': 'T8',
                  '16': 'T9', '17': 'T10', '18': 'T11', '19': 'T12',
                  '20': 'L1', '21': 'L2', '22': 'L3', '23': 'L4', '24': 'L5',
                  '25': 'S1', '26': 'S2'}

list_labels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]

average_vert_length = {'C1': 0.0, 'C2': 20.176514191661337, 'C3': 17.022090519403065, 'C4': 17.842111671016056,
                       'C5': 16.800356992319429, 'C6': 16.019212889311383, 'C7': 15.715854192723905,
                       'T1': 16.84466163681078, 'T2': 19.865049296865475, 'T3': 21.550165130933905,
                       'T4': 21.761237991438083, 'T5': 22.633281372803687, 'T6': 23.801974227738132,
                       'T7': 24.358357813758332, 'T8': 25.200266294477885, 'T9': 25.315272064638506,
                       'T10': 25.501856729317133, 'T11': 27.619238824308123, 'T12': 29.465119270009946,
                       'L1': 31.89272719870084, 'L2': 33.511890474486449, 'L3': 35.721413718617441}


def download_data_template(path_data='./', name='example', force=False):
    """
    This function downloads the example data and return the path where it was downloaded.
    :param path_data: destination path where to download the data
    :return: absolute destination path
    """

    # Download data
    if name == 'example':
        data_name = 'data'
        url = 'https://www.neuro.polymtl.ca/_media/downloads/sct/20181128_example_data_template.zip'
    elif name == 'icbm152':
        data_name = 'icbm152'
        url = 'https://www.neuro.polymtl.ca/_media/downloads/sct/20181128_icbm152.zip'
    else:
        raise ValueError('ERROR: data name is wrong. It should be either \'example\' or \'icbm152\'')

    if os.path.isdir(path_data + data_name) and not force:
        print (os.path.abspath(path_data + data_name) + '/')
        return os.path.abspath(path_data + data_name) + '/'

    verbose = 2
    try:
        tmp_file = download_data(url, verbose)
    except (KeyboardInterrupt):
        sct.printv('\nERROR: User canceled process.\n', 1, 'error')

    # Check if folder already exists
    sct.printv('\nCheck if folder already exists...')
    if os.path.isdir(path_data + data_name):
        sct.printv('WARNING: Folder ' + path_data + data_name + ' already exists. Removing it...', 1, 'warning')
        shutil.rmtree(path_data + data_name, ignore_errors=True)

    # unzip
    unzip(tmp_file, path_data, verbose)

    sct.printv('\nRemove temporary file...')
    os.remove(tmp_file)

    absolute_path = os.path.abspath(path_data + data_name) + '/'
    os.chmod(absolute_path, 0o755)

    return absolute_path


def read_dataset(fname_json='configuration.json'):
    """
    This function reads a json file that describes the dataset, including the list of subjects as well as
    suffix for filenames (centerline, disks, segmentations, etc.).
    The function raises an exception if the file is missing or if required fields are missing from the json file.
    :param fname_json: path + file name to json description file.
    :return: a dictionary with all the fields contained in the json file.
    """
    if not os.path.isfile(fname_json):
        raise ValueError('File ' + fname_json + ' doesn\'t seem to exist. Please check your data.')

    with open(fname_json) as data_file:
        dataset_info = json.load(data_file)

    dataset_temp = {}
    for key in dataset_info:
        dataset_temp[str(key)] = dataset_info[key]
    dataset_info = dataset_temp

    dataset_info['path_data'] = str(dataset_info['path_data'])
    dataset_info['path_template'] = str(dataset_info['path_template'])
    dataset_info['suffix_centerline'] = str(dataset_info['suffix_centerline'])
    dataset_info['suffix_disks'] = str(dataset_info['suffix_disks'])
    dataset_info['subjects'] = [str(subject) for subject in dataset_info['subjects']]
    if 'suffix_segmentation' in dataset_info:
        dataset_info['suffix_segmentation'] = str(dataset_info['suffix_segmentation'])
    
    return dataset_info

def generate_centerline(dataset_info, contrast='t1',  regenerate=False ,algo_fitting='linear',smooth = 0, degree=None, minmax=None):
    """
    This function generates spinal cord centerline from binary images (either an image of centerline or segmentation)
    :param dataset_info: dictionary containing dataset information
    :param contrast: {'t1', 't2'}
    :return list of centerline objects
    """
    path_data = dataset_info['path_data']
    list_subjects = dataset_info['subjects']
    list_centerline = []

    current_path = os.getcwd()

    tqdm_bar = tqdm(total=len(list_subjects), unit='B', unit_scale=True, desc="Status", ascii=True)
    for subject_name in list_subjects:
        path_data_subject = path_data + "/" + subject_name + '/' + contrast + '/'
        fname_image = path_data + "/" + subject_name + '/' + contrast + '/' + contrast + '.nii.gz'
        fname_image_centerline = path_data_subject + contrast + dataset_info['suffix_centerline']
        fname_image_disks = path_data_subject + contrast + dataset_info['suffix_disks'] + '.nii.gz'

        # if centerline exists, we load it, if not, we compute it
        if os.path.isfile(fname_image_centerline + '.npz')  and not regenerate:
            print("Centerline from subject "+ subject_name +" exists and will not be recomputed!")
            centerline = Centerline(fname=fname_image_centerline + '.npz')
        else:
            sct.printv('Extracting centerline from ' + path_data + '/' + subject_name)
            # extracting intervertebral disks
            im = Image(fname_image)
            native_orientation=im.orientation
            im.change_orientation('RPI')
            im_seg=Image(fname_image_centerline + ".nii.gz").change_orientation('RPI')
            im_discs = Image(fname_image_disks).change_orientation('RPI')

            coord = im_discs.getNonZeroCoordinates(sorting='z', reverse_coord=True)
            
            coord_physical = []
            for c in coord:
                if c.value <= 26 or c.value in [48, 49, 50, 51, 52]:  # 22 corresponds to L2
                    c_p = list(im_discs.transfo_pix2phys([[c.x, c.y, c.z]])[0])
                    c_p.append(c.value)
                    coord_physical.append(c_p)


            param_centerline = ParamCenterline(algo_fitting=algo_fitting,contrast=contrast,smooth=smooth,degree=degree,minmax=minmax) 
            
            centerline = straightening._get_centerline(im_seg,param_centerline, 1)

            centerline.compute_vertebral_distribution(coord_physical)
            # im_centerline.change_orientation(native_orientation).save(f"{fname_image_centerline}.nii.gz")
            centerline.save_centerline(fname_output=fname_image_centerline)
        
        list_centerline.append(centerline)
        tqdm_bar.update(1)
    tqdm_bar.close()
    os.chdir(current_path)
    return list_centerline


def compute_ICBM152_centerline(dataset_info):
    """
    This function extracts the centerline from the ICBM152 brain template
    :param dataset_info: dictionary containing dataset information
    :return:
    """
    path_data = dataset_info['path_data']

    if not os.path.isdir(path_data + 'icbm152/'):
        download_data_template(path_data=path_data, name='icbm152', force=False)

    image_disks = Image(path_data + 'icbm152/mni_icbm152_t1_tal_nlin_sym_09c_disks_manual.nii.gz')
    coord = image_disks.getNonZeroCoordinates(sorting='z', reverse_coord=True)
    coord_physical = []

    for c in coord:
        if c.value <= 22 or c.value in [48, 49, 50, 51, 52]:  # 22 corresponds to L2
            c_p = list(image_disks.transfo_pix2phys([[c.x, c.y, c.z]])[0])
            c_p.append(c.value)
            coord_physical.append(c_p)

    x_centerline_fit, y_centerline_fit, z_centerline, x_centerline_deriv, y_centerline_deriv, z_centerline_deriv = smooth_centerline(
        path_data + 'icbm152/mni_icbm152_t1_centerline_manual.nii.gz', algo_fitting='nurbs',
        verbose=0, nurbs_pts_number=300, all_slices=False, phys_coordinates=True, remove_outliers=False)

    centerline = Centerline(x_centerline_fit, y_centerline_fit, z_centerline,
                            x_centerline_deriv, y_centerline_deriv, z_centerline_deriv)

    centerline.compute_vertebral_distribution(coord_physical, label_reference='PMG')
    return centerline


def average_centerline(list_centerline, dataset_info, use_ICBM152=True, use_label_ref=None):
    """
    This function compute the average centerline and vertebral distribution, that will be used to create the
    final template space.
    :param list_centerline: list of Centerline objects, for all subjects
    :param dataset_info: dictionary containing dataset information
    :return: points_average_centerline: list of points (x, y, z) of the average spinal cord and brainstem centerline
             position_template_disks: index of intervertebral disks along the template centerline
    """

    if use_ICBM152:
        # extracting centerline from ICBM152
        centerline_icbm152 = compute_ICBM152_centerline(dataset_info)

    # extracting distance of each disk from C1
    list_dist_disks = []
    for centerline in list_centerline:
        list_dist_disks.append(centerline.distance_from_C1label)

    # computing length of each vertebral level
    length_vertebral_levels = {}
    for dist_disks in list_dist_disks:
        for disk_label in dist_disks:
            if disk_label == 'PMJ':
                length = abs(dist_disks[disk_label] - dist_disks['PMG'])
            elif disk_label == 'PMG':
                length = abs(dist_disks[disk_label] - dist_disks['C1'])
            else:
                index_current_label = list_labels.index(labels_regions[disk_label])
                next_label = regions_labels[str(list_labels[index_current_label + 1])]
                if next_label in dist_disks:
                    length = abs(dist_disks[disk_label] - dist_disks[next_label])
                else:
                    if disk_label in average_vert_length:
                        length = average_vert_length[disk_label]
                    else:
                        length = 0.0

            if disk_label in length_vertebral_levels:
                length_vertebral_levels[disk_label].append(length)
            else:
                length_vertebral_levels[disk_label] = [length]

    # averaging the length of vertebral levels
    average_length = {}
    for disk_label in length_vertebral_levels:
        mean = np.mean(length_vertebral_levels[disk_label])
        std = np.std(length_vertebral_levels[disk_label])
        average_length[disk_label] = [disk_label, mean, std]

    # computing distances of disks from C1, based on average length
    distances_disks_from_C1 = {'C1': 0.0}
    if 'PMG' in average_length:
        distances_disks_from_C1['PMG'] = -average_length['PMG'][1]
        if 'PMJ' in average_length:
            distances_disks_from_C1['PMJ'] = -average_length['PMG'][1] - average_length['PMJ'][1]
    for disk_number in list_labels:
        if disk_number not in [50, 49, 1] and regions_labels[str(disk_number)] in average_length:
            distances_disks_from_C1[regions_labels[str(disk_number)]] = distances_disks_from_C1[regions_labels[str(disk_number - 1)]] + average_length[regions_labels[str(disk_number)]][1]

    # calculating disks average distances from C1
    average_distances = []
    for disk_label in distances_disks_from_C1:
        mean = np.mean(distances_disks_from_C1[disk_label])
        std = np.std(distances_disks_from_C1[disk_label])
        average_distances.append([disk_label, mean, std])

    # averaging distances for all subjects and calculating relative positions
    average_distances = sorted(average_distances, key=lambda x: x[1], reverse=False)
    number_of_points_between_levels = 100
    disk_average_coordinates = {}
    points_average_centerline = []
    label_points = []
    average_positions_from_C1 = {}
    disk_position_in_centerline = {}

    for i in range(len(average_distances)):
        disk_label = average_distances[i][0]
        average_positions_from_C1[disk_label] = average_distances[i][1]

        for j in range(number_of_points_between_levels):
            relative_position = float(j) / float(number_of_points_between_levels)
            if disk_label in ['PMJ', 'PMG']:
                relative_position = 1.0 - relative_position
            list_coordinates = [[]] * len(list_centerline)
            for k, centerline in enumerate(list_centerline):
                list_coordinates[k] = centerline.get_coordinate_interpolated(disk_label, relative_position)

            # average all coordinates
            average_coord = np.nanmean(list_coordinates, axis=0)
            # add it to averaged centerline list of points
            points_average_centerline.append(average_coord)
            label_points.append(disk_label)
            if j == 0:
                disk_average_coordinates[disk_label] = average_coord
                disk_position_in_centerline[disk_label] = i * number_of_points_between_levels

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

    position_template_disks = {}

    if use_ICBM152:
        coord_ref = np.copy(centerline_icbm152.points[centerline_icbm152.index_disk[label_ref]])
        for disk in average_length:
            if disk in ['C1', 'PMJ', 'PMG']:
                position_template_disks[disk] = centerline_icbm152.points[centerline_icbm152.index_disk[disk]]
            else:
                coord_disk = coord_ref.copy()
                coord_disk[2] -= average_positions_from_C1[disk] - average_positions_from_C1[label_ref]
                position_template_disks[disk] = coord_disk
    else:
        coord_ref = np.array([0.0, 0.0, 0.0])
        for disk in average_length:
            coord_disk = coord_ref.copy()
            coord_disk[2] -= average_positions_from_C1[disk] - average_positions_from_C1[label_ref]
            position_template_disks[disk] = coord_disk

    # change centerline to be straight below reference if using ICBM152
    if use_ICBM152:
        index_straight = disk_position_in_centerline[label_ref]
    else:  # else: straighten every points along centerline
        index_straight = 0

    points_average_centerline_template = []
    for i in range(0, len(points_average_centerline)):
        current_label = label_points[i]
        if current_label in average_length:
            length_current_label = average_length[current_label][1]
            relative_position_from_disk = float(i - disk_position_in_centerline[current_label]) / float(number_of_points_between_levels)
            temp_point = np.copy(coord_ref)

            if i >= index_straight:
                index_current_label = list_labels.index(labels_regions[current_label])
                next_label = regions_labels[str(list_labels[index_current_label + 1])]
                if next_label not in average_positions_from_C1:
                    temp_point[2] = coord_ref[2] - average_positions_from_C1[current_label] - relative_position_from_disk * length_current_label
                else:
                    temp_point[2] = coord_ref[2] - average_positions_from_C1[current_label] - abs(relative_position_from_disk * (average_positions_from_C1[current_label] - average_positions_from_C1[next_label]))
            points_average_centerline_template.append(temp_point)

    if use_ICBM152:
        # append ICBM152 centerline from PMG
        points_icbm152 = centerline_icbm152.points[centerline_icbm152.index_disk[label_ref]:]
        points_icbm152 = points_icbm152[::-1]
        points_average_centerline = np.concatenate([points_icbm152, points_average_centerline_template])
    else:
        points_average_centerline = points_average_centerline_template

    return points_average_centerline, position_template_disks


def generate_initial_template_space(dataset_info, points_average_centerline, position_template_disks):
    """
    This function generates the initial template space, on which all images will be registered.
    :param points_average_centerline: list of points (x, y, z) of the average spinal cord and brainstem centerline
    :param position_template_disks: index of intervertebral disks along the template centerline
    :return:
    """

    # initializing variables
    path_template = dataset_info['path_template']
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
    template_space.save(path_template + 'template_space.nii.gz', dtype='uint8')

    # generate template centerline as an image
    image_centerline = template_space.copy()
    for coord in points_average_centerline:
        coord_pix = image_centerline.transfo_phys2pix([coord])[0]
        if 0 <= coord_pix[0] < image_centerline.data.shape[0] and 0 <= coord_pix[1] < image_centerline.data.shape[1] and 0 <= coord_pix[2] < image_centerline.data.shape[2]:
            image_centerline.data[int(coord_pix[0]), int(coord_pix[1]), int(coord_pix[2])] = 1
    image_centerline.save(path_template + 'template_centerline.nii.gz', dtype='float32')

    # generate template disks position
    coord_physical = []
    image_disks = template_space.copy()
    for disk in position_template_disks:
        label = labels_regions[disk]
        coord = position_template_disks[disk]
        coord_pix = image_disks.transfo_phys2pix([coord])[0]

        coord = coord.tolist()
        coord.append(label)
        coord_physical.append(coord)
        if 0 <= coord_pix[0] < image_disks.data.shape[0] and 0 <= coord_pix[1] < image_disks.data.shape[1] and 0 <= coord_pix[2] < image_disks.data.shape[2]:
            image_disks.data[int(coord_pix[0]), int(coord_pix[1]), int(coord_pix[2])] = label
        else:
            sct.printv(str(coord_pix))
            sct.printv('ERROR: the disk label ' + str(disk) + ' is not in the template image.')
    image_disks.save(path_template + 'template_disks.nii.gz', dtype='uint8')

    # generate template centerline as a npz file
    x_centerline_fit, y_centerline_fit, z_centerline, x_centerline_deriv, y_centerline_deriv, z_centerline_deriv = smooth_centerline(
        path_template + 'template_centerline.nii.gz', algo_fitting='nurbs', verbose=0, nurbs_pts_number=4000,
        all_slices=False, phys_coordinates=True, remove_outliers=True)
    centerline_template = Centerline(x_centerline_fit, y_centerline_fit, z_centerline,
                                     x_centerline_deriv, y_centerline_deriv, z_centerline_deriv)
    centerline_template.compute_vertebral_distribution(coord_physical)
    centerline_template.save_centerline(fname_output=path_template + 'template_centerline')


def straighten_all_subjects(dataset_info, normalized=False, contrast='t1'):
    """
    This function straighten all images based on template centerline
    :param dataset_info: dictionary containing dataset information
    :param normalized: True if images were normalized before straightening
    :param contrast: {'t1', 't2'}
    """
    path_data = dataset_info['path_data']
    path_template = dataset_info['path_template']
    list_subjects = dataset_info['subjects']

    if normalized:
        fname_in = contrast + '_norm.nii.gz'
        fname_out = contrast + '_straight_norm.nii.gz'
    else:
        fname_in = contrast + '.nii.gz'
        fname_out = contrast + '_straight.nii.gz'

    # straightening of each subject on the new template
    tqdm_bar = tqdm(total=len(list_subjects), unit='B', unit_scale=True, desc="Status", ascii=True)
    for subject_name in list_subjects:
        path_data_subject = path_data + subject_name + '/' + contrast + '/'

        # go to output folder
        sct.printv('\nStraightening ' + path_data_subject)
        os.chdir(path_data_subject)
        sct.run('sct_straighten_spinalcord'
                ' -i ' + fname_in +
                ' -s ' + contrast + dataset_info['suffix_centerline'] + '.nii.gz'
                ' -ldisc_input ' + contrast + dataset_info['suffix_disks'] + '.nii.gz'
                ' -dest ' + path_template + 'template_centerline.nii.gz'
                ' -ldisc_dest ' + path_template + 'template_disks.nii.gz'
                ' -disable-straight2curved'
                ' -param threshold_distance=1', verbose=1)

        image_straight = Image(sct.add_suffix(fname_in, '_straight'))
        image_straight.save(fname_out, dtype='float32')

        tqdm_bar.update(1)
    tqdm_bar.close()


def copy_preprocessed_images(dataset_info, contrast='t1'):
    path_data = dataset_info['path_data']
    path_template = dataset_info['path_template']
    list_subjects = dataset_info['subjects']

    fname_in = contrast + '_straight_norm.nii.gz'

    tqdm_bar = tqdm(total=len(list_subjects), unit='B', unit_scale=True, desc="Status", ascii=True)
    for subject_name in list_subjects:
        path_data_subject = path_data + subject_name + '/' + contrast + '/'
        os.chdir(path_data_subject)
        shutil.copy(fname_in, path_template + subject_name + '_' + contrast + '.nii.gz')
        tqdm_bar.update(1)
    tqdm_bar.close()


def normalize_intensity_template(dataset_info, fname_template_centerline=None, contrast='t1', verbose=1):
    """
    This function normalizes the intensity of the image inside the spinal cord
    :param fname_template: path to template image
    :param fname_template_centerline: path to template centerline (binary image or npz)
    :return:
    """

    path_data = dataset_info['path_data']
    list_subjects = dataset_info['subjects']
    path_template = dataset_info['path_template']

    average_intensity = []
    intensity_profiles = {}

    tqdm_bar = tqdm(total=len(list_subjects), unit='B', unit_scale=True, desc="Status", ascii=True)

    # computing the intensity profile for each subject
    for subject_name in list_subjects:
        path_data_subject = path_data + subject_name + '/' + contrast + '/'
        if fname_template_centerline is None:
            fname_image = path_data_subject + contrast + '.nii.gz'
            fname_image_centerline = path_data_subject + contrast + dataset_info['suffix_centerline'] + '.nii.gz'
        else:
            fname_image = path_data_subject + contrast + '_straight.nii.gz'
            if fname_template_centerline.endswith('.npz'):
                fname_image_centerline = None
            else:
                fname_image_centerline = fname_template_centerline

        image = Image(fname_image)
        nx, ny, nz, nt, px, py, pz, pt = image.dim

        if fname_image_centerline is not None:
            # open centerline from template
            number_of_points_in_centerline = 4000
            x_centerline_fit, y_centerline_fit, z_centerline, x_centerline_deriv, y_centerline_deriv, z_centerline_deriv = smooth_centerline(
                fname_image_centerline, algo_fitting='nurbs', verbose=0,
                nurbs_pts_number=number_of_points_in_centerline,
                all_slices=False, phys_coordinates=True, remove_outliers=True)
            centerline_template = Centerline(x_centerline_fit, y_centerline_fit, z_centerline,
                                             x_centerline_deriv, y_centerline_deriv, z_centerline_deriv)
        else:
            centerline_template = Centerline(fname=fname_template_centerline)

        x, y, z, xd, yd, zd = centerline_template.average_coordinates_over_slices(image)

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
        arr_int.sort(key=lambda x: x[0])  # and make sure it is ordered with z

        def smooth(x, window_len=11, window='hanning'):
            """smooth the data using a window with requested size.
            """

            if x.ndim != 1:
                raise ValueError, "smooth only accepts 1 dimension arrays."

            if x.size < window_len:
                raise ValueError, "Input vector needs to be bigger than window size."

            if window_len < 3:
                return x

            if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
                raise ValueError, "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"

            s = np.r_[x[window_len - 1:0:-1], x, x[-2:-window_len - 1:-1]]
            if window == 'flat':  # moving average
                w = np.ones(window_len, 'd')
            else:
                w = eval('np.' + window + '(window_len)')

            y = np.convolve(w / w.sum(), s, mode='same')
            return y[window_len - 1:-window_len + 1]

        # Smoothing
        intensities = [c[1] for c in arr_int]
        intensity_profile_smooth = smooth(np.array(intensities), window_len=50)
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
        path_data_subject = path_data + subject_name + '/' + contrast + '/'
        fname_image = path_data_subject + contrast + '_straight.nii.gz'

        image = Image(fname_image)
        nx, ny, nz, nt, px, py, pz, pt = image.dim

        image_image_new = image.copy()
        image_image_new.change_type(dtype='float32')
        for i in range(nz):
            image_image_new.data[:, :, i] *= average_intensity / intensity_profiles[subject_name][i]

        # Save intensity normalized template
        fname_image_normalized = sct.add_suffix(fname_image, '_norm')
        image_image_new.save(fname_image_normalized)


def create_mask_template(dataset_info, contrast='t1'):
    path_template = dataset_info['path_template']
    subject_name = dataset_info['subjects'][0]

    template_mask = Image(path_template + subject_name + '_' + contrast + '.nii.gz')
    template_mask.data *= 0.0
    template_mask.data += 1.0
    template_mask.save(path_template + 'template_mask.nii.gz')

    # if mask already present, deleting it
    if os.path.isfile(path_template + 'template_mask.mnc'):
        os.remove(path_template + 'template_mask.mnc')
    sct.run('nii2mnc ' + path_template + 'template_mask.nii.gz ' + ' ' + path_template + 'template_mask.mnc')

    return path_template + 'template_mask.mnc'


def convert_data2mnc(dataset_info, contrast='t1'):
    path_template = dataset_info['path_template']
    list_subjects = dataset_info['subjects']

    path_template_mask = create_mask_template(dataset_info, contrast)

    output_list = open('subjects.csv', "wb")
    writer = csv.writer(output_list, delimiter =',', quotechar=',', quoting=csv.QUOTE_MINIMAL)

    tqdm_bar = tqdm(total=len(list_subjects), unit='B', unit_scale=True, desc="Status", ascii=True)
    for subject_name in list_subjects:
        fname_nii = path_template + subject_name + '_' + contrast + '.nii.gz'
        fname_mnc = path_template + subject_name + '_' + contrast + '.mnc'

        # if mask already present, deleting it
        if os.path.isfile(fname_mnc):
            os.remove(fname_mnc)

        sct.run('nii2mnc ' + fname_nii + ' ' + fname_mnc)

        writer.writerow([fname_mnc, path_template_mask])

        tqdm_bar.update(1)
    tqdm_bar.close()

    output_list.close()