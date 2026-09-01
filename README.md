# Center-brain

A docker-based container for re-centering an MRI brain volume by applying pure voxel shifts - and resampling.

The resampled version is mapped to atlas MNI305.

![Idea](https://github.com/HaukeBartsch/centerbrain/blob/main/idea.png)

## What it does

- Reads an input image in .nii, .nii.gz or .mgz format
- Uses HD-BET to detect and extract the brain (and mask)
- Computes the brain's center of mass in x, y, and z
- Shifts the original image so the brain is also centered inside the field of view (no resampling), result is saved as output volume.
- Register the centered brain against MNI305.corr.nii.gz using rigid registration and brain masks
- Write out the registered re-centered brain as *_reg2mni305.nii.gz

## Build the container

```bash
docker build -t centerbrain -f Dockerfile .
```

## Run the container

```bash
docker run --rm -it \
  -v `pwd`/data:/data \
  centerbrain \
  /data/head.nii.gz /data/head_centered.nii.gz
```

or

```bash
docker run -it --rm -v `pwd`/data:/data centerbrain /data/head.mgz /data/head_centered.mgz
```

The above commands will create a `data/head_centered.mgz` and a `data/head_centered_reg2mni305.mgz` volume.

## Notes

- The container expects a 3D image that can be loaded by nibabel.
- The output (output 1) is created by shifting voxels and preserving the original image grid. This 'soft' approach keeps all image information as-is, no degradation of image quality due to resampling.
- The _reg2mni305.* output (output 2) includes a rigid (translation and rotation) to MNI space. This approach resamples the image intensities.
- For best results, use a brain MRI with good contrast and sufficient coverage.

