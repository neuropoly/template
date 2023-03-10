"""
Update NIFTI header of the histological template to be aligned with the ICBM152 PAM50 template.

Context: the original histological template was aligned with the original PAM50 template. However, the original PAM50
template was updated to the align with the ICBM152 space. Thus, also the histological template has to be updated.

Details: https://github.com/spinalcordtoolbox/spinalcordtoolbox/issues/2179

Jan Valosek
"""

import os
import argparse

import nibabel as nib


def get_parser():
    """
    parser function
    """
    parser = argparse.ArgumentParser(
        description='Update NIFTI header of the histological template to be aligned with the ICBM152 PAM50 template.',
        prog=os.path.basename(__file__).rstrip('.py')
    )
    parser.add_argument(
        '-i',
        metavar="<file>",
        required=True,
        help="Histological image to be updated. Example: PAM50_200um_AVF.nii.gz"
    )
    parser.add_argument(
        '-new-PAM50',
        metavar="<file>",
        required=True,
        help="New ICBM152 PAM50 template. Example: $SCT_DIR/data/PAM50/template/PAM50_t1.nii.gz"
    )
    parser.add_argument(
        '-old-PAM50',
        metavar="<file>",
        required=True,
        help="Old PAM50 template (https://osf.io/jmfpw). Example: 20180813_PAM50/template/PAM50_t1.nii.gz"
    )

    return parser


def load_nifti(fname):
    """
    Load NIFTI file, get header and fetch qform and sform
    :param fname: NIFTI file name
    :return: nii, header, qform, sform
    """
    nii = nib.load(fname)
    header = nii.header
    qform = header.get_qform()
    sform = header.get_sform()
    return nii, header, qform, sform


def main():
    # Parse the command line arguments
    parser = get_parser()
    args = parser.parse_args()

    # Load new ICBM152 PAM50 template
    _, _, qform_pam50, sform_pam50 = load_nifti(args.new_PAM50)

    # Load the 20180813_PAM50 template (https://osf.io/jmfpw)
    _, _, qform_pam50_20180813, sform_pam50_20180813 = load_nifti(args.old_PAM50)

    # Load histological image
    nii, nii_header, qform, sform = load_nifti(args.i)

    # Compute translation between ICBM152 PAM50 and 20180813_PAM50 and add it to the histological image
    qform[1,3] = qform[1,3] + (qform_pam50[1,3] - qform_pam50_20180813[1,3])
    qform[2,3] = qform[2,3] + (qform_pam50[2,3] - qform_pam50_20180813[2,3])
    sform[1,3] = sform[1,3] + (sform_pam50[1,3] - sform_pam50_20180813[1,3])
    sform[2,3] = sform[2,3] + (sform_pam50[2,3] - sform_pam50_20180813[2,3])

    # Update the qform and sform of the histological image
    nii.set_qform(qform)
    nii.set_sform(sform)

    # Save the new NIFTI image
    out_fname = args.i.replace('.nii.gz', '_new_header.nii.gz')
    nib.save(nii, out_fname)
    print('Saved: ' + out_fname)


if __name__ == '__main__':
    main()
