
# Data Source Manifest

## Master data

| Dataset | Source | License / provenance | Transformation |
|---|---|---|---|
| Plants | Synthetic generator | Original synthetic data | Generated using fixed seed |
| Production lines | Synthetic generator | Original synthetic data | Linked to generated plants |
| Machines | Synthetic generator | Original synthetic data | Linked to generated production lines |
| Sensors | Synthetic generator | Original synthetic data | Linked to generated machines |
| Operating shifts | Synthetic generator | Original synthetic data | Generated for each plant |
| Parts | Synthetic generator | Original synthetic data | Generated from predefined catalog |
| Technicians | Synthetic generator | Original synthetic data | Generated from synthetic names |

## Reproducibility

- Generator: `scripts/generate_master_data.py`
- Seed: `20261022`
- Starter command: `python -m scripts.generate_master_data --mode starter`
- Full command: `python -m scripts.generate_master_data --mode full`

## External data

No external datasets are used in this phase.
No external URLs, licenses or attributions are applicable.
