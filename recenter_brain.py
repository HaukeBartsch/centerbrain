#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import tempfile
import SimpleITK as sitk
from pathlib import Path

import nibabel as nib
import numpy as np


def run_command(command: list[str], *, description: str) -> None:
    print(f"[center-brain] {description}: {' '.join(command)}")
    subprocess.run(command, check=True)


def ensure_dependency(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"Required dependency '{name}' was not found in the container PATH")


def shift_array_with_zero_padding(data: np.ndarray, shifts: np.ndarray) -> np.ndarray:
    shifted = data.astype(np.float32, copy=True)
    for axis, shift in enumerate(shifts):
        if shift == 0:
            continue

        next_shifted = np.zeros_like(shifted, dtype=np.float32)
        if shift > 0:
            src_slices = [slice(None)] * data.ndim
            dst_slices = [slice(None)] * data.ndim
            src_slices[axis] = slice(0, data.shape[axis] - shift)
            dst_slices[axis] = slice(shift, data.shape[axis])
            next_shifted[tuple(dst_slices)] = shifted[tuple(src_slices)]
        else:
            src_slices = [slice(None)] * data.ndim
            dst_slices = [slice(None)] * data.ndim
            src_slices[axis] = slice(-shift, data.shape[axis])
            dst_slices[axis] = slice(0, data.shape[axis] + shift)
            next_shifted[tuple(dst_slices)] = shifted[tuple(src_slices)]

        shifted = next_shifted
    return shifted


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-center a 3D MRI brain using HD-BET and voxel shifts plus reg against mni305")
    parser.add_argument("input", help="Input NIfTI image (.nii or .nii.gz, or .mgz)")
    parser.add_argument("output", help="Output NIfTI image (.nii or .nii.gz, or .mgz)")
    args = parser.parse_args()

    ensure_dependency("hd-bet")
    ensure_dependency("fslmaths")
    ensure_dependency("fslstats")

    # There are two different libraries reading the input and output formats (sitk and nibabel).
    # Only nibabel can work with .mgz files (as output format). The registration using sitk does
    # not seem to be able to write .mgz files.
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    exts_out = output_path.suffixes   # either [".nii", ".gz"] or [".nii"] or [".mgz"]
    exts_in = input_path.suffixes     # either [".nii", ".gz"] or [".nii"] or [".mgz"]
    if len(exts_out) == 0:
        raise SystemExit("[center-brain] Provide an extension for the output filename")

    # What is working is using the input as .nii.gz (or .nii) and the output as .nii.gz as well.
    # So convert first either of them to tmp and undo at the end of the script.
    output_path_no_ext = str(output_path)
    for word in exts_out:
        output_path_no_ext = output_path_no_ext.replace(word, "")

    output_path2 = Path(args.output).resolve().parent / Path(output_path_no_ext + "_reg2mni305.nii.gz")

    if not input_path.is_file():
        raise SystemExit(f"[center-brain] Input is not a file: {input_path}")

    # now do something like this to the input if its .mgz
    if ".nii" not in exts_in:
        # convert to .nii.gz first and use that instead
        im = nib.load(str(input_path))
        # create a .nii.gz version of the .mgz input
        input_path2 = Path(args.output).resolve().parent / Path(Path(input_path).name).with_suffix(".nii.gz")
        nib.save(im, str(input_path2))
        print(f"[center-brain] Continue to work with a .nii.gz version ({input_path2}) of the input {input_path}")
        input_path = input_path2

    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = nib.load(str(input_path))
    if img.ndim != 3:
        raise SystemExit("[center-brain] Only 3D NIfTI images are supported")

    with tempfile.TemporaryDirectory(prefix="center-brain-", dir="/tmp", delete=False) as tmpdir:
        tmpdir_path = Path(tmpdir)
        # brain only image (we ignore this output)
        brain_path = tmpdir_path / "brain_extracted.nii.gz"
        # 0/1 mask
        mask_path = tmpdir_path / "brain_extracted_bet.nii.gz"

        run_command(["hd-bet", "-i", str(input_path), "-o", str(brain_path), "-device", "cpu", "--disable_tta", "--save_bet_mask"], description="Running brain extraction")
        # run_command(["fslmaths", str(brain_path), "-thr", "0.5", "-bin", str(mask_path)], description="Creating brain mask")

        stats = subprocess.run(["fslstats", str(mask_path), "-C"], check=True, capture_output=True, text=True)
        com = np.array([float(value) for value in stats.stdout.strip().split()], dtype=float)

        shape = np.array(img.shape, dtype=float)
        target_center = (shape - 1.0) / 2.0
        shifts = np.round(target_center - com).astype(int)
        print(f"[center-brain] Shifts (x, y, z): {shifts}")

        float_shifts = target_center - com
        rel_shift_pct = -float_shifts / shape * 100.0
        print(f"[center-brain] Relative shifts (x, y, z): {rel_shift_pct.round(2).tolist()} % of image size")

        # Relative shifts in mm using voxel dimensions from the affine
        # Column norms of the 3×3 upper-left affine submatrix → voxel size (mm) per axis
        # voxel_sizes = np.linalg.norm(img.affine[:3, :3], axis=0)  # (dx, dy, dz) in mm
        voxel_sizes = img.header.get_zooms()[:3]  # (dx, dy, dz) in mm
        rel_shift_mm = float_shifts * voxel_sizes
        print(f"[center-brain] Relative shifts (x, y, z): {rel_shift_mm.round(2).tolist()} mm")

        data = img.get_fdata(dtype=np.float32)
        shifted_data = shift_array_with_zero_padding(data, shifts)

        new_img = nib.Nifti1Image(shifted_data, img.affine, header=img.header.copy())
        nib.save(new_img, str(output_path))
        if Path(output_path).suffix == ".mgz":
            # save as .nii as well
            nib.save(new_img, str(Path(output_path).with_suffix(".nii.gz")))

        # Use the brain and its brain mask to run a final registration (rigid) against mni305.cor.nii.gz
        # This dataset comes from freesurfer which in turn creates it as mgz from the MINC dataset 
        # /share/mni_autoreg/average_305.mnc.
        atlas_path = Path(__file__).parent / "mni305.cor.nii.gz"
        mnimask_path = Path(__file__).parent / "mni305_head_bet.nii.gz"
        if not atlas_path.exists():
            raise SystemExit(f"[center-brain] Atlas file not found: {atlas_path}")
        atlas = sitk.ReadImage(str(atlas_path), sitk.sitkFloat32)
        if Path(output_path).suffix == ".mgz":
            # load the file here as .nii.gz
            # we need that version for 
            moving = sitk.ReadImage(str(Path(output_path).with_suffix(".nii.gz")), sitk.sitkFloat32)
        else:
            # load the file as .nii
            moving = sitk.ReadImage(str(output_path), sitk.sitkFloat32)

        # Use SimpleITK for registration
        elastixImageFilter = sitk.ElastixImageFilter()
        parameterMap = sitk.GetDefaultParameterMap("rigid")
        parameterMap["DefaultPixelValue"] = ("0",)
        parameterMap["ErodeMovingMask"] = ("false",)
        parameterMap["ErodeFixedMask"] = ("false",)
        parameterMap["NumberOfSpatialSamples"] = ("3000",)
        parameterMap["MaximumNumberOfIterations"] = ("1000",)
        parameterMap["AutomaticTransformInitialization"] = ("true",)
        parameterMap["AutomaticTransformInitializationMethod"] = ("GeometricalCenter",)
        parameterMapVector = []
        parameterMapVector.append(parameterMap)
        elastixImageFilter.SetParameterMaps(parameterMapVector)  
        elastixImageFilter.SetFixedImage(atlas)
        elastixImageFilter.SetFixedMask(sitk.ReadImage(str(mnimask_path), sitk.sitkUInt8))
        elastixImageFilter.SetMovingImage(moving)
        elastixImageFilter.SetMovingMask(sitk.ReadImage(str(mask_path), sitk.sitkUInt8))
        try:
            elastixImageFilter.Execute()
            resultImage = elastixImageFilter.GetResultImage()
            # always .nii.gz
            sitk.WriteImage(resultImage, str(output_path2))
        except:
            print(f"[center-brain] Error occurred while processing {brain_path}")
        if exts_out[0] == ".mgz":
            # convert .nii.gz file to mgz
            print(f"[center-brain] Wrote re-centered image to {output_path}")
            # it should always be a .nii.gz due to conversion earlier
            im = nib.load(str(output_path2))
            nib.save(im, str(output_path))
        else:
            print(f"[center-brain] Wrote re-centered image to {output_path2}")


if __name__ == "__main__":
    main()
