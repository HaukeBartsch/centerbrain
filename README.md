# Center-brain

A docker-based container for re-centering an MRI brain volume by applying pure voxel shifts.

Extension: map to MNI305 as an alternative - requires to resample the original data.

## What it does

- Reads an input NIfTI image in .nii or .nii.gz format
- Uses HD-BET to detect and extract the brain
- Creates a binary brain mask with FSL tools, install FSL with "curl -Ls https://fsl.fmrib.ox.ac.uk/fsldownloads/fslconda/releases/getfsl.sh | sh -s"
- Computes the brain center of mass in x, y, and z
- Shifts the original image so the brain is centered inside the field of view without resampling
- Writes a re-centered output image as .nii.gz
- Loads the MNI305.corr.nii.gz atlas and registers the re-centered brain (rigid)
- Write out the registered re-centered brain as .nii.gz

## Build the container

```bash
docker build -t centerbrain -f Dockerfile .
```

## Run the container

```bash
docker run --rm -it \
  -v `pwd`/data:/data \
  centerbrain /data/head.nii.gz /data/head_centered.nii.gz
```

or

```bash
docker run -it --rm -v `pwd`/data:/data centerbrain /data/head.mgz /data/head_centered.mgz
```


## Notes

- The container expects a 3D image that can be loaded by nibabel.
- The output is created by shifting voxels and preserving the original image grid.
- For best results, use a brain MRI with good contrast and sufficient coverage.

