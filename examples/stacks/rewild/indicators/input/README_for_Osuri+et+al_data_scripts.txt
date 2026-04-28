Osuri, A. M., S. Kasinathan, M. Siddhartha, D. Mudappa, and T. R. S. Raman. 2019. Effects of restoration on
tree communities and carbon storage in rainforest fragments of the Western Ghats, India. Ecosphere 
DOI:10.1002/ecs2.2860

Dataset description

File: tree_data.csv
Description: Data on adult trees (>= 30 cm gbh) from 20x20m plots in restored, naturally regenerating and 
benchmark rainforests in the Anamalai Hills, India.
Columns:
X: Row ID
Date: Plot sampling date
Forest_name: Name of fragment/remnant/benchmark forest
Site: Restoration/benchmark site name
Site_code: Restoration/benchmark site code 
Plot_code: Plot code
Plant_year: Year of planting
age_2017: age in the year 2017
Treatment: Forest type - actively restored (Active), naturally regenerating (Passive) and benchmark
species: Species name
Genus: Genus
GBH1-11: Girth at breast height of up to 10 stems (cm)
GBH: Effective GBH (GBH1^2+GBH2^2+...GBHN^2)^0.5 (cm)
DBH: Effective diameter at breast height (cm)
Height: Tree height (m)
Remarks
HD_include: Whether to include (1) or not (0)  in height-diameter ratio assessment (cut/broken trees excluded)
accpt.nam: Accepted name (The Plant List)
accpt.gen: Accepted genus (The Plant List)
accpt.nam.full: Complete accepted name (The Plant List)

File: regen_data.csv
Description: Data on seedlings and saplings from 5x5m plots in restored, naturally regenerating and 
benchmark rainforests in the Anamalai Hills, India.
Columns:
X: Row ID
Date: Plot sampling date
Forest_name: Name of fragment/remnant/benchmark forest
Site_code: Restoration/benchmark site code 
Plot_code: Plot code
Treatment: Forest type - actively restored (Active), naturally regenerating (Passive) and benchmark
Year_restored: Year of planting
Species.name: Species name
Notes
regen: No. of saplings
acc_name: Accepted name (The Plant List)
acc_gen: Accepted genus (The Plant List)
acc_name_full: Complete accepted name (The Plant List)

File: species_traits.csv
Description: Tree species type and wood density data.
Columns:
X: Row ID
sp_name: Species name
acc_name: Accepted name (The Plant List)
acc_gen: Accepted genus (The Plant List)
acc_name_full: Complete accepted name (The Plant List)
Habt_New: Species type - Mature forest species, Secondary forest species, Introduced species, and Unknown affinity
Wden_sp: Species wood density (g/cm^3)
Wden_gen: Genus average wood density (g/cm^3)

File: Resto_site_info.csv
Description: Information on study sites.
Columns:
Forest_name: Name of fragment/remnant/benchmark forest
Site_name: Restoration/benchmark site name
Type: Forest type - actively restored (Active), naturally regenerating (Passive) and benchmark
Long: Longitude
Lat: Latitude
Year_restored: Year of planting
Site_code: Restoration/benchmark site code 
Plot_code: Plot code
Can_vis: Canopy cover - visual estimate (%)
Can_den: Canopy cover - densiometer estimate  (%)
Plant_den: Estimated no. of saplings planted per hectare
Plant_div: Estimated no. of species planted per hectare
Chave_E: Coefficient from Chave et al. (2014) used for estimating tree heights for missing observations
dist_PA: Distance to contiguous forest (m)
Description
Rest_area: Area restored (ha)
Area: Size of remnant (sq.m)


