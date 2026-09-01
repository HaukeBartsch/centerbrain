# Center-brain

A docker-based container for re-centering an MRI brain volume by applying pure voxel shifts - and resampling.

**Issue addressed**: MMPS and FreeSurfer might have issues with T1-weighted MR images that have too much neck as part of the acquisition. If such processing fails this tool can re-center the brain (adding and removing as needed). Restarting MMPS / FreeSurfer might work now for these previously failed processing runs.

The resampled version is mapped to atlas MNI305.

![Idea](https://github.com/HaukeBartsch/centerbrain/blob/main/idea.png)
Fig.: Sketch on the left represents a sagittal view of an MRI volume - the brain is not centered in the field of view and rotated upwards (arrow). Sketch on the right represents the same sagittal view after centering by adding and removing slices (output 1) and after an additional registration to the MNI-305 space (output 2).

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
- For best image acquisition the field of view should include sufficient background in anterior and posterior direction (wrap-around effect of the nose, shadow visible otherwise inside the posterior cortex). Also, the field of view should be angled to have both the anterior and posterior commissures in a single axial plane. Fully include the cerebellum in the scan.
