### **Organisation Details:**

1. **Organisation Name:** Nature Conservation Foundation (NCF)  
2. **Organisation Mission:** NCF focuses on conserving India’s wildlife and ecosystems through research, habitat restoration, and engaging local communities. In line with this, they aim to restore native biodiversity of forests by growing native plants in nurseries, contributing to ecological restoration across various regions.

#### **Priority Challenges:**

1. **End to End Process Workflow Tracking:** There are various stages involved in the overall process and there is a need to manage inflow and outflow at each stage.  
2. **Funnel Mapping:** Overall difficulty in tracking top of the funnel metrics such as inflow of seeds and bottom of the funnel for plants, across a life cycle of 2-3 years.   
3. **Decentralised Data Management:** Currently, all data is manually tracked using [**Excel spreadsheets**](https://docs.google.com/spreadsheets/d/1JZdkZIqGbeEmO4K8LECZNk3tFiXPnjEP/edit?gid=1360871130#gid=1360871130), leading to inefficiencies in data sharing and management.

#### **Urgency of Problem:**

1. **High**: The manual system is insufficient for scaling across multiple nurseries and properly managing the stock, workflow, and seed tracking.

### **Priority Requirements from an Ideal Tech Solution:**

1. **Comprehensive Workflow Management:** The software should be able to track seed and plant stock at every stage (from stages of collection, cleaning, and germination to planting etc) and for each species.  
2. **Insightful Analytics:** The ability to generate reports and monitor the stock of each species in real-time without relying on Excel spreadsheets, with features to handle failed germination tracking.  
3. **Customizable Workflow Stages (Low Priority):** Flexibility to accommodate different workflows across  nurseries and track the progress of different batches and species through the nursery lifecycle.

#### **Potential Users for the System:**

1. System Manager \- Add or Remove/Manage Users and Full Access  
2. Project Manager \- Full Access   
   1. Primary Use \- Dashboards, Reports, Check Data Sanity  
   2. Data entered at user level should be accepted/verified by the project manager before it is submitted.   
3. Seed Collecting Team \- User Level  
   1. Keep track of seed collection and planting.  
4. Nursery Team \- User Level  
   1. Keep track of sapling production and overall stock and diversity.

Note \- Most users are savvy with mobile apps. However, mobile/internet coverage is poor to nonexistent in many field locations. So the app has to work offline and sync later. Shouldn't be too battery-usage heavy.

**High Level Process Workflow [(Native Plant Nursery Tracker)](https://docs.google.com/spreadsheets/d/1JZdkZIqGbeEmO4K8LECZNk3tFiXPnjEP/edit?gid=1008073378#gid=1008073378)**

* Seeds are collected from high-diversity forests by field teams, and batches tagged with details like date of collection, species, quantity etc. A unique ID can be provided to seeds batch to identify and track important details throughout the lifecycle.   
* After collection, the seeds go through a **cleaning process** before being planted in nurseries. Tracking each batch of seeds from collection through to planting is important to monitor progress and success rates.  
* The nursery has 5 sections (A,B,C,D,E) and a room. Each section will have a different number of beds or  substrates. Seeds/saplings can be moved from sections A \- D based on different growth stages.   
* Seeds then go through the **germination process**, where it’s important to track success or failure at various stages. Saplings are tagged with date of germination, species and quantity of seeds. A unique ID can be provided to saplings.   
* Transplanting \- Not all seeds/seedlings go through a transplanting stage, but many species with very tiny seeds are usually grown in soil beds and then transplanted as individual plants into individual nursery covers (sleeves) at the right stage of growth.  
* Immature and rotten seeds are discarded at the nursery and not planted.   
* Failed seeds (planted but failed to germinate) need to be recorded during the germination monitoring. Covers with failed seeds are usually re-used afresh later.  
* The planting (section E) stage can take upto 1-2 years as well.

**System Expectations**

* The software should allow the user to record a (growing) **master list of species** that will then be available for use across the database/tables with consistent names.   
  * Ref to Tab “seedCollection” [here.](https://docs.google.com/spreadsheets/d/1JZdkZIqGbeEmO4K8LECZNk3tFiXPnjEP/edit?gid=1008073378#gid=1008073378)   
  * Also capture additional details   
    * Habit: Tree/Shrub/Liana/Climber/Grass/Herb/Aquatic etc  
    * Fruit Size: Large/Medium/Small/Tiny etc   
    * Seed Size: Large/Medium/Small/Tiny etc  
    * Seed No: Average number of Seeds per fruit  
* Need custom named sections and beds to be setup for each nursery.   
* Location of each batch is tracked as the plants are stacked and moved across various sections/beds of the nursery.   
* Seed collection may happen by a different team and will need to record details like location of collection, species, photos etc. Then the batch is handed over to the nursery team, which will process, select mature seeds, discard rotten ones etc and do the planting, monitoring etc. So seed collection and nursery dashboards may be different and involve different users.  
* Managing and **tracking inventory** for each species at different stages (collected, cleaned, germinated, planted) across multiple nurseries is currently inefficient, as it relies on Excel spreadsheets.  
* Dashboards to Study Species \- Monitoring Germination \- Earliest/Last Date, Max rate of Germination

#### **Implementation Plan:**

* NCF operates **12 native plant nurseries** pan India to support ecological restoration.   
* Initial implementation is planned for 1 major nursery in the Nilgiri region.   
* NCF will promote adoption of the software to the other **native plant nurseries** through the Ecological Restoration Alliance \- India ([https://era-india.org](https://era-india.org)) website and nursery portal (in development).  
* This may expand to more nurseries focusing on horticulture in future as well (long term plan).

**Proposed System Overview**

1. Inventory and Stock Management   
   1. Seed Collection Module   
      1. User \- Collecting Team  
      2. Seed/wildling Collection  
         1. location, species approximate number of fruits/seeds or wildings collected, brought to nursery and delivered to Nursery Sorting Team  
   2. Nursery Batching Module  
      1. User \- Nursery Team  
      2. Sorting and Batching \-  sorting, counting, discarding rotten etc, take final count and  allocate to batches.   
      3. Seed Sowing \- Keeping track of number, nursery section/bed/substrate \-- (substrate can be covers, tray, soil bed etc)  
      4. Germination Monitoring \- Additional/optional module for select batches to track germination closely

2. Operations and Workflow Management  
   1. Nursery upkeep and maintenance for nursery team  
      1.  Transplanting \- when small seeds go from trays or beds or smaller covers to larger covers  
      2. Moving \- when plants are shifted by bed or section  
      3. Upkeep \- sometimes plants die and are removed or are in poor condition and kept aside for recovery

#### **Timeline Expectations**

* Next planting season \- Aug 2025