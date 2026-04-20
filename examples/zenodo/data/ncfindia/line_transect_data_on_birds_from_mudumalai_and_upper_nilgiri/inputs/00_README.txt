This dataset contains data on bird communities from variable-width line transect surveys carried out in 1995-96 in the Mudumalai Wildlife Sanctuary (now Tiger Reserve) and Upper Nilgiris, Tamil Nadu, India. The data were collected on a project of the Centre for Ecological Sciences, Indian Institute of Science, Bangalore.

GEOGRAPHICAL AREA: Mudumalai Wildlife Sanctuary (now Tiger Reserve) and Upper Nilgiris, Tamil Nadu, India

TAXONOMIC SCOPE: Birds

ACKNOWLEDGEMENT: I am grateful to Dr R. Sukumar for the opportunity to survey these transects and to P. Pavithra and Palani for help with data.

METHODS

Bird data are from 1200 m long (0.75 miles) line transect surveys surveyed typically in about 100-120 min duration in the early morning hours. The methods for bird sampling are as described in Raman (2003) and in this doctoral thesis:
Raman, T. R. S. 2001. Community ecology and conservation of mid-elevation tropical rainforest bird communities in the southern Western Ghats, India. PhD thesis, Indian Institute of Science, Bangalore.

All transects were censused during the first 3 h after sunrise when bird activity was highest in the area walking at a slow, uniform pace. All birds seen (perched or flying under the canopy) or heard were recorded as to species, number (wherever possible) and perpendicular distance in the following metre classes: 0–5, 5–10, etcwith the further distance classes being wider to minimize errors in distance estimation.

USAGE NOTES

Besides this 00_README.txt file, this dataset contains the following 3 comma-delimited text files with data in columns as explained below.

01_niltrans.csv
This contains information on the line transects
date: date of survey in year-month-date format
transect: name of transect
stratum: habitat stratum
decimalLatitude: latitude in decimal degrees N
decimalLongitude: longitude in decimal degrees E
coordinateUncertaintyInMeters: approximate uncertainty in metres as exact location is unknown
duration: duration of survey in minutes
startTime: transect start time in the morning in hh:mm format
endTime: transect end time in the morning in hh:mm format
weather: notes on weather
remarks: other remarks

02_nilbirds.csv
This contains the transect bird data
date: date of survey in year-month-date format
transect: name of transect
startTime: transect start time in the morning in hh:mm format
endTime: transect end time in the morning in hh:mm format
verbatimID: bird species name as originally identified and used
eBirdIndiaName: bird species common name as per the eBird / Clements India list
scientificName: bird species Latin binomial as per the eBird / Clements India list
number: total number of individuals counted (minimum number in case of aural detections or flocks; for detections noted as 'flock' in remarks, number was assigned a minimum of 3)
perpendicularDistanceInMetres: perpendicular distance band in metres 
heardSeenFlying: H - heard, s - Seen, F - Flying
location: additional notes on location
leftRight: L - left, R - right
remarks: notes if any
mixedFlock: Yes or No indicating whether the particular detection was in a mixed species flock



