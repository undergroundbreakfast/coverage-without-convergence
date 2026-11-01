# More hospitals report artificial intelligence use but geographic divides persist

Analysis software accompanying the study of population proximity to hospitals reporting artificial intelligence use in the 2022 and 2024 American Hospital Association surveys.

The software calculates geographic coverage, population-weighted inequality, rurality and income comparisons, reporting diagnostics, missing-response scenarios, and implementation-stage summaries. Proximity is an estimated geographic measure; it does not establish service availability, patient exposure, or clinical benefit.

## Getting started

Use Python 3.14 and the pinned scientific dependencies:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/check_code.py
python scripts/verify_release.py
```

These checks run without the study data. They test production calculations, script imports, and file integrity.

To run the study analyses, arrange the prepared inputs as described in the [input specification](docs/inputs.md), then run:

```sh
python scripts/check_inputs.py
python scripts/run_analysis.py --stage numerical
python scripts/run_analysis.py --stage figures
```

See the [reproduction guide](docs/reproduction.md) for configuration and the [output index](docs/outputs.md) for the figures and tables supported by each script.

## Repository contents

| Location | Contents |
| --- | --- |
| `code/` | Analysis, plotting, supplementary tabulation, and optional PDF-formatting scripts |
| `scripts/` | Input checks, execution order, code checks, and archive packaging |
| `tests/` | Tests of the production calculations using synthetic inputs |
| `docs/` | Input specification, reproduction instructions, and output index |
| `CITATION.cff`, `.zenodo.json` | Software citation and repository metadata |
| `release_manifest.json` | File inventory and SHA-256 checksums |

Local inputs belong in `data/` and generated files in `outputs/`; neither directory is distributed.

## Data and reproduction scope

The scripts begin with the study's prepared hospital extracts, population panel, and geographic inputs. Licensed hospital records are not included. Researchers must arrange access to the American Hospital Association survey data under the applicable terms; obtaining those files alone does not reconstruct the prepared study inputs. Raw-survey extraction, geocoding, and some earlier supplementary analyses are outside this package. The [input specification](docs/inputs.md) and [output index](docs/outputs.md) describe these boundaries.

The final figures and aggregate source summaries accompany the article and its supplementary material. This software archive contains code and documentation, rather than historical figure or table assets.

## Citation and license

Use the metadata in [CITATION.cff](CITATION.cff) to cite the software. Version 1.0.0 has reserved Zenodo DOI [10.5281/zenodo.23870377](https://doi.org/10.5281/zenodo.23870377); the record is currently a draft. The uploaded archive matches the [consolidated software snapshot](https://github.com/undergroundbreakfast/coverage-without-convergence/tree/690dce8801dc0bc4be1d60d959e97ae4008a90f9). Author-owned code and documentation are distributed under the [MIT license](LICENSE). The license does not cover survey data, third-party geography, or fonts.

Contact: Aaron Johnson, aj3248@drexel.edu.

## Earlier versions

The [original submission release](https://github.com/undergroundbreakfast/coverage-without-convergence/releases/tag/v137-submission) and the [earlier analysis snapshot](https://github.com/undergroundbreakfast/coverage-without-convergence/tree/v143-code) remain available unchanged. Their figures and numbering belong to those versions. See [CHANGELOG.md](CHANGELOG.md) for the consolidated software version.
