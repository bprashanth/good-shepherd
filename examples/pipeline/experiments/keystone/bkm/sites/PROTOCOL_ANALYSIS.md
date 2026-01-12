# Field Protocol and KML Feature Analysis

## Overview
This document analyzes the match between the field protocol (from `field_protocol_bkm.pdf`) and the available KML features, identifying what exists and what needs to be created or requested from users.

## Field Protocol Requirements

### 1. Study Sites (Shola Patches)
**Protocol Requirement:**
- Four shola patches total
- Two close to settlement (150-350m distance)
- Two far from settlement (>450m distance)

**KML Features Found:**
- ✅ `Bikkapathimund_Shola_A` (Polygon)
- ✅ `Biikkapathimund_Shola_B` (Polygon)
- ❌ Missing: Two additional shola patches (C and D)

**Data Required:**
- Site identification/name
- Distance from settlement center
- Proximity classification (close/far)

### 2. Transects
**Protocol Requirement:**
- Transects placed along the side of shola patch facing the settlement
- Transects radiate into shola from edge, perpendicular to edge
- Minimum 50m separation between neighboring transects
- Total transect length: 130m

**KML Features Found:**
- ✅ Transect lines: `A_T1`, `A_T2`, `A_T3`, `A_T4`, `A_T5`, `A_T6`, `A_T7` (LineString)
- ✅ Transect lines: `B_T1`, `B_T2`, `B_T3`, `B_T4`, `B_T5` (LineString)
- ✅ Transect start points: `T1`, `T2`, `T3`, `T4`, `T5`, `T6`, `T7` (Point)
- ✅ Transect start points: `B_T1`, `B_T2`, `B_T3`, `B_T4`, `B_T5` (Point)
- ✅ Intermediate segments: `60m 1`, `60m 2`, `60m 3`, `60m 4`, `60m 10` (LineString) - likely plot segments

**Data Required:**
- Transect ID
- Associated shola patch (Site A or B)
- Distance from settlement
- Orientation/direction

### 3. Plots (10x10m)
**Protocol Requirement:**
- Five plots per transect
- Placed at: 0m (edge), 10m, 20m, 40m, 60m from shola edge
- Total transect length: 130m (10+10+20+20+20+20+20)

**KML Features Found:**
- ✅ Multiple plot polygons with density classifications:
  - `A_HD-1`, `A_HD-2`, `A_HD-3`, `A_HD-4` (High Density)
  - `A_MD-1`, `A_MD-2`, `A_MD-3`, `A_MD-4`, `A_MD-5`, `A_MD-6`, `A_MD-7`, `A_MD-8` (Medium Density)
  - `A_LD-1`, `A_LD-2`, `A_LD-3` (Low Density)
  - `A_VHD-1`, `A_VHD-2`, `A_VHD-3`, `A_VHD-5`, `A_VHD-6`, `A_VHd-4` (Very High Density)
- ⚠️ Note: Plot naming suggests they are categorized by Cestrum density, not by transect/position

**Data Required per Plot:**
- Plot ID (should link to transect and position)
- DBH measurements for all woody individuals ≥1cm
- Multi-stemmed individuals: record all stems ≥1cm, sum later
- Soil moisture at center (Dry+, Dry-, Normal, Wet-, Wet+)
- Canopy openness at center (4 readings in cardinal directions, convert to %)
- Other features: dung, signs of lopping, trails, etc.

### 4. Subplots (2x2m)
**Protocol Requirement:**
- Four subplots per 10x10m plot
- Placed at corners of the larger plot
- Numbered 1-4 clockwise, starting with left corner closest to edge

**KML Features Found:**
- ❌ No explicit subplot features in KML
- ⚠️ Subplots need to be generated or requested from user

**Data Required per Subplot:**
- Subplot number (1-4)
- Number of seedlings (non-woody individuals)
- Number of saplings (woody individuals <1.3m OR ≥1.3m but DBH <1cm)
- Ocular estimate of grass cover (%)
- Ocular estimate of bare ground cover (%)
- Soil moisture (Dry+, Dry-, Normal, Wet-, Wet+)

### 5. Additional Protocol Elements (Objective 2)
**Protocol Requirement:**
- Two restoration plots:
  1. Near male cremation ground: 50x50m plot with ≥20 1x1m quadrats
  2. Behind temple: 100x25m plot with same protocol

**KML Features Found:**
- ❌ No explicit restoration plot features found
- ⚠️ These may need to be added or are in a separate KML file

**Data Required:**
- Pre and post monsoon monitoring
- Grass cover, bare ground, litter
- Species present

## Summary: Matching Status

| Protocol Element | KML Status | Action Required |
|-----------------|------------|-----------------|
| Shola Sites (4 total) | 2 found | Request 2 additional sites or confirm if only 2 are used |
| Transects | ✅ Found (A_T1-7, B_T1-5) | Link to plots, verify positions |
| 10x10m Plots | ✅ Found (many with density labels) | Need to link to transects and positions (0m, 10m, 20m, 40m, 60m) |
| 2x2m Subplots | ❌ Not found | Generate from plot corners OR request from user |
| Restoration plots | ❌ Not found | Request from user or separate KML |

## Data Entry Requirements by Feature Type

### Site Level
- Site name/ID
- Distance from settlement
- Proximity classification

### Transect Level
- Transect ID
- Associated site
- Start point coordinates
- Direction/orientation

### Plot Level (10x10m)
- Plot ID
- Associated transect
- Position along transect (0m, 10m, 20m, 40m, 60m)
- DBH data (all woody individuals ≥1cm)
- Soil moisture (center)
- Canopy openness (center, 4 readings)
- Other observations (dung, lopping, trails)

### Subplot Level (2x2m)
- Subplot number (1-4)
- Associated plot
- Seedling count
- Sapling count
- Grass cover (%)
- Bare ground cover (%)
- Soil moisture

## Questions for User

1. Are there only 2 shola patches (A and B) or should there be 4 total?
2. How are the plot polygons (A_HD-1, A_MD-1, etc.) related to transects? Do they correspond to specific positions along transects?
3. Should subplots be automatically generated at plot corners, or do you have specific subplot locations?
4. Are the restoration plots (cremation ground, temple) in a separate KML file?
5. What is the relationship between the "60m 1", "60m 2" line segments and the plots?

