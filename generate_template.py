"""
Run this script with the following command (replace N by the number of subjects):

python -m scoop -n N -vvv generate_template.py

"""

from scoop import futures, shared

from ipl.model import generate_nonlinear

if __name__ == '__main__':
    # setup data for parallel processing
    generate_nonlinear.generate_nonlinear_model_csv('subjects.csv',
                                    work_prefix='model_nl_all',
                                    options={'symmetric': True,
                                             'protocol': [{'iter': 4, 'level': 8},
                                                          {'iter': 4, 'level': 4},
                                                          {'iter': 4, 'level': 2},
                                                          {'iter': 4, 'level': 1}],
                                             'refine': True
                                             }
                                    )