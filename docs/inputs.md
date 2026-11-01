# Prepared input specification

The analyses use a fixed study frame: 6,095 geocoded hospitals in 2022, 6,076 in 2024, and 238,433 census block groups containing 331,449,208 residents. The primary reporting counts are 1,118 and 1,737 hospitals. These describe the geocoded analysis frame, which differs from full-survey totals.

## Directory layout

Paths are relative to `PAPER2_DATA_DIR`, or `data/` by default:

```text
hospitals/
  years/2022/hospital_ai_robotics_enriched_2022.parquet
  years/2024/hospital_ai_robotics_enriched_2024.parquet
panel/
  transition_detail.csv
context/
  rucc2023.csv
  chr2024.csv
  2020_Gaz_counties_national.zip
geography/
  USA_BlockGroups_2020Pop.geojson
  tl_2024_us_county.shp
  tl_2024_us_county.shx
  tl_2024_us_county.dbf
  tl_2024_us_county.prj
```

## Hospital extracts

Both years require unique `hospital_id` values and these columns: `ai_flag`, `robo_flag`, `bsc`, `county_fips`, `state`, `latitude`, `longitude`, `cntrl`, `serv`, and `sysname`. State values are two-letter abbreviations. `bsc` supplies staffed-bed counts; ownership, service type, and system-name text retain the categories expected by the reporting models.

The 2022 items are `wfaipsn`, `wfaippd`, `wfaiss`, `wfaiart`, and `wfaioacw`. The access scripts use their Yes/No text. The division summary also requires the corresponding `_num` columns, coded 1 for Yes, 0 for No, and missing for unknown responses.

The 2024 items are `aiopef`, `aipatd`, `airevc`, `aiscop`, `aisswm`, `aitiot`, `clinai`, `clnoai`, `diagai`, `papcai`, `pcoeai`, `pdmrai`, `pophai`, and `surgai`. Each requires an analytical `_num` column: 0 = Not implementing, 1 = Exploring, 2 = Piloting/testing, 3 = Expanding, 4 = Fully integrated. Unknown responses are missing. These analytical codes differ from the original survey codes. The original label columns are required for implementation-stage validation.

Primary use means any Yes in 2022 and any Expanding or Fully Integrated response in 2024. Operational-only, clinical-only, and fully integrated definitions are calculated separately. Preserve identifier types and leading zeros.

## Population panel and geography

`transition_detail.csv` contains unique 12-character `GEOID` values and `POPULATION`, `county_fips`, `state_fips`, `drive_2022`, `drive_2024`, `within_2022`, and `within_2024`. Drive columns contain the study's proxy minutes; within columns indicate proximity within 30 minutes. Population weights and the geographic frame remain fixed across years.

`USA_BlockGroups_2020Pop.geojson` contains the original block-group polygons, `GEOID`, and `population`, with its coordinate reference system. It combines 2020 Census population counts with Census boundaries. Supply the same prepared layer used for the study. Original polygons determine representative points in EPSG:5070; points are transformed to EPSG:4326 for distance calculations. Simplified display geometry must not replace those original polygons.

The 2024 Census county boundaries support Connecticut's planning-region reconciliation. Income and resampling retain the legacy county geography described in the study.

## County context

| File | Source and required structure |
| --- | --- |
| `rucc2023.csv` | U.S. Department of Agriculture 2023 Rural-Urban Continuum Codes export, including `FIPS`, `Attribute`, and `Value`; `Attribute == RUCC_2023` identifies the codes |
| `chr2024.csv` | County Health Rankings 2024 export, retaining its two-row header structure and the fields `5-digit FIPS Code` and `Median Household Income raw value` |
| `2020_Gaz_counties_national.zip` | Census 2020 county Gazetteer; one tab-separated text file containing `GEOID` and `ALAND_SQMI` |

## Access and preparation boundary

Licensed hospital records and detailed derived spatial inputs are not distributed. Arrange survey access with the American Hospital Association. The scripts do not perform raw-survey extraction, hospital geocoding, or construction of the prepared population/geography layers. The schemas above specify the inputs; they do not replace those preparation steps. Questions about the study extracts and their availability can be directed to Aaron Johnson, aj3248@drexel.edu.
