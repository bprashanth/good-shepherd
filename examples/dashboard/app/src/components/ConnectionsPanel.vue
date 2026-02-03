<template>
    <div class="panel">

        <!-- Study results title -->
        <div class="study-row title-row">
                <div class="contact-info">CONTACT</div>
                <div class="study-name">NAME</div>
                <div class="status-info">STATUS</div>
                <div class="sensor-info">SENSORS</div>
        </div>

        <!-- Study Results row: 
            contact: study name: status: sensor badges
        -->
        <div
        class="study-row"
        v-for="study in studies"
        :key="study.name"
        @mouseover="showBoundary(study.maps.boundary)"
        @mouseleave="clearBoundary"
        @click="selectStudy(study)">

            <div class="contact-info">
                <img
                :src="study.contact.image" 
                :alt="`Contact for ${study.contact.name}`" 
                class="badge contact">
            </div>

            <div class="study-name">
                {{ study.name }}
            </div>

            <div class="status-info">
                <div
                :class="study.status === 'active' ? 'status-active' : 'status-complete'">
                {{ study.status }}
            </div>

            </div>
            
            <div class="sensor-info">
                <img
                v-for="image in getMatchingBadges(study.sensors)"
                :key="image"
                :src="image"
                :alt="`Badge for ${image}`"
                class="badge">
            </div>

            <a
            :href="getDataverseLink(study.dataverseLink)"
            target="_blank"
            >
                <div v-if="study.public === true" class="status-active">public</div>
                <div v-if="study.public === false" class="status-complete">locked</div>
            </a>

        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, defineEmits } from 'vue';

// Studies contain the list of studies related to the main study in the 
// professor panel. 
const studies = ref([]);

// localHoveredBoundary contains the geojson boundary of the study 
// being hovered.
const localHoveredBoundary = ref(null);
const emit = defineEmits(['update-hovered-boundary']);

onMounted(async () => {
    try {
        const response = await fetch('/data/studyIndex.json');
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }
        studies.value = await response.json();
    } catch (error) {
        console.error('Error loading studyIndex.json: ', error);
    }
});

const selectStudy = (connection) => {
    console.log(connection.dataverseLink);
};

// Convert dataverseLink to actual url. 
const getDataverseLink = (dataverseLink) => {
    if (!dataverseLink) return '#';
    const { schema, data } = dataverseLink;
      return `/dataverse?schema=${encodeURIComponent(schema)}&data=${encodeURIComponent(data)}`;
}

const getMatchingBadges = (sensors) => {
    console.log(sensors);
    if (!sensors) return [];
    return sensors.map(sensor => `/data/images/${sensor}.png`);
};

// showBoundary retrieves the geoJson from the file in study.maps.boundary 
// and pipes it as a prop to the map pane. 
const showBoundary = async (boundaryPath) => {
    try {
        const response = await fetch(boundaryPath);
        if (!response.ok) {
            throw new Error(`Failed to fetch boundary: ${boundaryPath}`);
        }
        localHoveredBoundary.value = await response.json();
        emit('update-hovered-boundary', localHoveredBoundary.value);
    } catch (error) {
        console.error(error);
    }
};

const clearBoundary = () => {
    localHoveredBoundary.value = null;
    emit('update-hovered-boundary', localHoveredBoundary.value);
};

</script>

<style scoped>
.panel {
    overflow-y: auto;
    height: 100%;
    width: 100%;
    background-color: #282c34;
    border-radius: 8px;
    color: #afaeae;
    font-family: monospace;
}

.title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: bold;
    color: #807e7e;
    padding: 10px 20px;
}

.study-row {
    border-bottom: 0.1em solid rgba(255, 255, 255, 0.1);
    font-size: 1.2em;
    font-weight: bold;
    padding: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.study-row:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}

.study-name {
    flex: 2;
    text-align: left;
}

.contact-info {
    flex: 1;
    text-align: left;
}

.status-info {
    flex: 1;
    text-align: center;
}

.sensor-info {
    flex: 2;
    display: flex;
    justify-content: flex-start;
    gap: 5px;
}

.badge {
    width: 50px; 
    height: 50px;
    border-radius: 50%;
    overflow: hidden;
    /* display: inline-block; */
    /* position: relative; */
    box-shadow: 0px 0px 15px rgba(0, 0, 0, 0.5);
    padding: 0.3em;
    /* background: linear-gradient(145deg, #FFD700, #B8860B); */
    border: 2px solid #317183;
    object-fit: cover;
    cursor: pointer;
} 

.badge.contact {
    background: linear-gradient(145deg, #844491, #0b25b8);
    /* border: 2px solid #020607; */
    /* border: none; */
} 

.status-active {
    border: 1px solid #197231;
    font-size: 0.7em;
    color: rgb(112, 167, 30);
    background: #173A1F;
    display: inline-block;
    margin: 5px;
    padding: 5px;
    border-radius: 4px;
}

.status-complete {
    border: 1px solid grey;
    font-size: 0.7em;
    color: grey;
    background: #25282e;
    display: inline-block;
    margin: 5px;
    padding: 5px;
    border-radius: 4px;
}

.dataverse-button,.lock-closed-button {
    margin-top: 10px;
    padding: 5px 15px;
    font-size: 0.7rem;
    background-color: #151B24;
    border: 1px solid #1E4173;
    color: white;
    border-radius: 5px;
    cursor:pointer;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    text-decoration: none;
}

.dataverse-button:hover {
    background-color: #1E4173;
}

.locked {
    color:rgba(255, 255, 255, 0.1);
}
</style>