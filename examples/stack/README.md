# Design

The idea here is to replicate the examples/ stack that starts at examples/web and has the following components today: 
* Entrypoit: `web/` -> this has cards for all the following 
* Experiment: `setup_wizard/`
* Phone pwa: `pwa/`
* Data: `forms/`
* Indicators: `indicators/`
* Alienwise: `alienwise/`


This is kind of a research focused stack, and i want to replicate it but re-do it with a practioners focus. so the design of the dirs within stack/, at the top level, map almost 1:1 with the stack in examples/ described in ./.agent/rules/project-context.md 

For the practioners stack,  we will instead have the following components
* Entrypoint: `examples/stack/web/` -> this has cards for all the following 
* Site selection: `examples/stack/setup_wizard/`
* Site Assesment: `examples/stack/pwa/`
* Plantwise: `examples/stack/plantwise/`
* Site Monitoring: `examples/stack/pwa/`
* Indicators: `examples/stack/indicators/`

Each of these sub-components is structured the same as the sub-components already in examples (their siblings). There is input/ and output/ and outputs.md - which has the description of how the next stack layer should use the output/ assets. Within that structure we will be  doing this: 

## Web 

The is the static html entrypoint to each layer of the stack. Just do this last, it basically is just a fancy index like the one in experiments/web. 

## Site selection

We enter this page on clicking the "Site selection" card, the use is prompted for a kml file just like in `examples/Experiment`. 

There is an aoi in `examples/stack/setup_wizard/input/`, see `examples/stack/setup_wizard/input/README.md`. We need to show that outline. (hull around monitoring points from `anr_sites.json`). This simulates the kml. 

We need to add 1. alpha earth  embeddings for that hull, 2. the tif files from  `examples/alienwise/output`. 

and have a dropdown that shows 
1. "benchmark similarity" - when chosen, malanobis distance from benchmark sites (which again you get from `anr_sites.json` is shown as a heatmap in the AOI. 
2. "Invasive probability" - when chosen, just like in alienwise a probability of invasive (all combined) > 80% heatmap is shown from the tifs. 
The output of this  stage would be exactly  one plot for the next stage. This plot must lie in the aoi. It will be  consumed by the site assesment. 

## Site Assesment 

The input of this site is exactly one monitoring plot from the output of site selection - show it in a similar style to the pwa code in `examples/pwa` - if need be copy that over and instrument it. But the idea is the user goes  to that plot, and submits a picture from each subplot. The picture will be one of lantana - they will upload it via file upload through the same file pwa interface plus button, just like in `examples/pwa`. The only difference is the app will show an advisory saying something like this is lantana, with some simple removal instructions. 

## Plantwise 

Now the user goes back to the desk, and opens  plantwise, which once again shows the same aoi as site selection but this time it has an overlay of the plot itself and  no layers. When they click on the plot, they get the same output as plantwise - which is basis a query in plantwise. At build time, give me the coord for the center of the plot, i will plug it in platnwise and give you a list of species to use. What this interface also needs to show is a list of nurseries. Rather, it will show a list of nurseries, and underthat, the list of species - ranked by nursery with most species first. Show 2 nurseries. We will choose the names at build time. 

## Site monitoring

Again this is a pwa phase. Just the same as site assesment, we can even reuse that code, the only difference is that while that one has the user upload a lantana pic this one has the user upload other pics (eg of forms with metadata). So basically just link back to the site assesment pwa phase, and just have a hardcode check like "if imagename lantana.jpg -> return lantana advisory" otherwise don't return anything. 

## Indicators 

This will have a simple 2 panel display. In left panel a list of portrait images  from input/ folder. On right panel, the set of indicators from the `examples/stack/indicators/input/` directory, most importantly the similarity score. These idicators should keep changing with the "next" button which also  changes the image. The idea is the user has taken some form data and photomonitoring images, and they use these two to measure the progress of their restoration. So as they click next they would see the indicator going up, and the image growing lusher.  
