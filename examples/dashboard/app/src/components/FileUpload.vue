<!-- FileUpload.vue
  - This component handles exactly one excel file upload
  - This file can have multiple sheets

  @props: none
  @emits: fileParsed
    {
      fullData: {
        sheetName1: {sheetJson},
        sheetName2: {sheetJson},
        ...
      },
      headerData: {
        sheetName1: [columnName1, columnName2, ...],
        sheetName2: [columnName1, columnName2, ...],
        ...
      }
    }
  @TODO:
  - Handle multiple file uploads
  - Handle file upload errors
  - Handle file upload progress
  - Styling
-->
<template>
  <div class="file-upload-container">
    <div class="logo">
      <img src="@/assets/logos/default.webp" alt="logo">
    </div>
    <label for="file-input" class="upload-label">
      <span class="file-placeholder">Upload a dataset...</span>
      <svg class="upload-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M11 15V3H13V15H11ZM12 19L7 14H17L12 19Z" fill="currentColor"/>
      </svg>
    </label>
    <input type="file" id="file-input" @change="handleFileUpload">
  </div>
</template>

<script setup>

import * as XLSX from 'xlsx';
import { defineEmits } from 'vue';

const emit = defineEmits(['fileParsed']);

const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, {type: 'array'});

        // Create two objects: one for full data, one for column headers
        const fullData = {};
        const headerData = {};

        console.log('workbook.SheetNames', workbook.SheetNames);

        workbook.SheetNames.forEach((sheetName) => {
          const sheet = workbook.Sheets[sheetName];
          // Get data with "header: 1" to get array format first
          const rawSheetJson = XLSX.utils.sheet_to_json(sheet, {header: 1});

          // Transform the data into objects
          const headers = rawSheetJson[0];
          const sheetJson = rawSheetJson.slice(1).map(row => {
            return headers.reduce((obj, header, index) => {
              obj[header] = row[index];
              return obj;
            }, {});
          });

          handleMergedCells(sheet, sheetJson, headers);
          fullData[sheetName] = sheetJson;
          headerData[sheetName] = headers;
        })

        // Emit both the full data and the headers
        emit('fileParsed', { fullData, headerData });
    };
    reader.readAsArrayBuffer(file);
};

/**
 * handleMergedCells handles cells that are merged across multiple rows.
 *
 * Currently this function only handles merges along the Y axis, i.e. merges
 * that span multiple rows. Merges that span multiple columns are not handled.
 *
 * @params
 * - sheet: The sheet object from the workbook
 * - sheetJson: The sheet object in json format, WITHOUT the header row
 * - headers: The headers of the sheet
 *
 * @returns: None
 *
 * The sheetJson is modified in place to handle merged cells.
 */
const handleMergedCells = (sheet, sheetJson, headers) => {

  // Sheet merges shows the first and last row, column of a merged cell. Eg:
  // {s: {r: 1, c: 1}, e: {r: 2, c: 1}}
  // This means that the cell at row 1, column 1 is merged with the cell at
  // 2, column 1, i.e
  // name | age
  //    A | 1
  //      | 2
  // For such a table, we want the json
  // {name: 'A', age: '1'}
  // {name: 'A', age: '2'}
  if (!sheet['!merges']) {
    console.log('No merged cells found');
    return;
  }

  sheet['!merges'].forEach(({ s, e }) => {
    const colIndex = s.c;
    // Why do we subtract 1 from the row indices?
    // sheetJson is offset by 1 row because we remove the header row. However sheet, from which we get the merges, is not offset. So the row indices
    const startRow = s.r - 1;
    const endRow = e.r - 1;

    const headerKey = headers[colIndex];
    if (!headerKey) return;

    const mergedValue = sheetJson[startRow]?.[headerKey];
    if (mergedValue == undefined) {
      console.log(
        'Merged value for row: ', startRow, 'col: ', colIndex, ' is undefined,  nothing to merge; Row:', sheetJson[startRow]);
      return;
    }
    for (let r = startRow + 1; r <= endRow; r++) {
      if (sheetJson[r]) {
        sheetJson[r][headerKey] = mergedValue;
      }
    }
  });
};

</script>


<style scoped>

/* File Upload Container
*
* This is the container that holds the file upload component.
* It is fixed to the top of the screen and centered.
* A note on the positioning (wrt to the viewport):
*  - The transform: left: 50% + translateX(-50%) is used to center it.
*  - Left 50% places the left edge of the container at 50% of the screen width.
*  - translateX(-50%) then moves it by half its own width.
*  - top: 10px is the distance from the top of the screen.
* A note on positioning of items within the container:
*  - display: flex moves the images adjacent to one another
*  - justify + align are used add spacing
*/
.file-upload-container {
  position: fixed;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);

  display: flex;
  align-items: center;
  justify-content: left;
  padding: 5px;
  width: 90%;
  max-width: 600px;
  z-index: 1000;

  /* background-color: #245a7b6b; */
  background-color: #151515;
  backdrop-filter: blur(10px);
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(194, 232, 235, 0.6),
              0 0 30px rgb(194, 231, 228);
}

.logo img {
  width: 40px;
  height: 40px;
  object-fit: contain;
}

.upload-label {
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}

.upload-icon {
  width: 20px;
  height: 20px;
  padding: 10px;
  border-left: 1px solid #C7C8C9;
  color: #C7C8C9;
}

.file-placeholder {
  color: #C7C8C9;
  font-size: 0.9em;
  font-style: italic;
  padding-left: 20px;
  font-family: monospace;
}

input[type="file"] {
  display: none;
}
</style>
