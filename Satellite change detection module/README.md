# Satellite Change Detection Module

This is a standalone computer-vision module for estimating project progress from satellite imagery.

Recommended default for this project: `levir-cd-public` preset.

It uses paired before/after imagery and binary change masks to train a lightweight segmentation model, then reports:

- IoU
- Dice score
- pixel accuracy
- a `percent_complete` estimate from the predicted change mask

## Quick Start

Run the synthetic smoke test first:

```powershell
python satellite_change_detector.py --smoke-test --epochs 2 --batch-size 4 --image-size 128
```

For a real dataset such as LEVIR-CD or OSCD:

```powershell
python satellite_change_detector.py \
  --a-dir C:/data/LEVIR-CD/train/A \
  --b-dir C:/data/LEVIR-CD/train/B \
  --mask-dir C:/data/LEVIR-CD/train/label \
  --epochs 5 --batch-size 4 --image-size 128
```

If you already extracted the dataset, you can also point the module at the root folder and let it resolve the standard layout:

```powershell
python satellite_change_detector.py --dataset-root C:/data/LEVIR-CD --dataset-name levir-cd --epochs 5 --batch-size 4
```

If you have a public ZIP mirror URL, the module can download and unpack it first:

```powershell
python satellite_change_detector.py --download-url https://example.com/LEVIR-CD.zip --dataset-name levir-cd --epochs 5 --batch-size 4
```

You can also use dataset-specific presets (recommended once mirror URLs are finalized):

```powershell
python satellite_change_detector.py --list-presets
python satellite_change_detector.py --dataset-preset levir-cd-public --preset-url https://example.com/LEVIR-CD.zip --epochs 5 --batch-size 4
```

If no data path flags are provided, the runner defaults to `--dataset-preset levir-cd-public` which now points to a public mirror by default.

To avoid passing URLs every time, set the preset URL environment variable first:

```powershell
$env:LEVIR_CD_PUBLIC_URL = "https://example.com/LEVIR-CD.zip"
python satellite_change_detector.py --dataset-preset levir-cd-public --epochs 5 --batch-size 4
```

You can keep these in a local env file by copying `.env.example` and setting your approved mirror URLs.

## Output

Results are written to `outputs/satellite_change_prototype/` by default:

- `satellite_change_smallnet.pt`
- `satellite_change_report.json`
- `smoke_data/` for synthetic tests

## Notes

`percent_complete` is the fraction of pixels marked as changed in the predicted mask. For real project reporting, normalize it against the planned project footprint polygon.