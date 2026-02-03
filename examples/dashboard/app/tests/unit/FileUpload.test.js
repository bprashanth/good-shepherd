import { describe, test, expect } from "vitest";
import { readFileSync } from 'fs';
import { join } from 'path';
import { shallowMount } from "@vue/test-utils";
import FileUpload from "@/components/FileUpload.vue";
import { waitFor } from "@testing-library/vue";

const testTimeout = 2000;
const testInterval = 50;


describe("FileUpload.vue", () => {
  test("should correctly process merged cells", async () => {
    const wrapper = shallowMount(FileUpload);

    const fileContent = readFileSync(join(__dirname, 'shola.xlsx'))
    const event = {
      target: {
        files: [
          new File(
            [fileContent],
            "shola.xlsx",
            { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }
          )
        ],
      },
    };

    await wrapper.vm.handleFileUpload(event);

    // Wait for FileReader to finish processing
    await waitFor(() => {
      expect(wrapper.emitted()).toHaveProperty("fileParsed");
    }, { timeout: testTimeout, interval: testInterval });

    const emittedEvents = wrapper.emitted();
    console.log('Emitted events:', emittedEvents);

    if (!emittedEvents.fileParsed) {
      throw new Error("File parsed event not emitted");
    }
    const [eventPayload] = emittedEvents.fileParsed.at(-1);
    console.log("FullData: ", eventPayload.fullData);
    console.log("HeaderData: ", eventPayload.headerData);

    // All notes should be the same, as the notes column is merged across all
    // rows. The first 3 and last 3 rows should have the same trees.
    var expectedNotes = eventPayload.fullData['Sheet1'][1].Notes;
    for (let i = 0; i < eventPayload.fullData['Sheet1'].length; i++) {
      expect(eventPayload.fullData['Sheet1'][i].Notes).toBe(expectedNotes);
    }

    for (let i = 0; i <= 3; i=i+3) {
      var expectedTree = eventPayload.fullData['Sheet1'][i].Trees;
      for (let j = i; j < i+3; j++) {
        expect(eventPayload.fullData['Sheet1'][j].Trees).toBe(expectedTree);
      }
    }
  });
});


describe("FileUpload.vue", () => {
  test("should correctly process a multi tab file", async () => {
    const wrapper = shallowMount(FileUpload);

    const fileContent = readFileSync(join(__dirname, 'tabs.xlsx'))
    const event = {
      target: {
        files: [
          new File(
            [fileContent],
            "tabs.xlsx",
            { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }
          )
        ],
      },
    };

    await wrapper.vm.handleFileUpload(event);

    // Wait for FileReader to finish processing
    await waitFor(() => {
      expect(wrapper.emitted()).toHaveProperty("fileParsed");
    }, { timeout: testTimeout, interval: testInterval });

    const emittedEvents = wrapper.emitted();
    console.log('Emitted events:', emittedEvents);

    if (!emittedEvents.fileParsed) {
      throw new Error("File parsed event not emitted");
    }
    const [eventPayload] = emittedEvents.fileParsed.at(-1);
    console.log("FullData: ", eventPayload.fullData);
    console.log("HeaderData: ", eventPayload.headerData);

    expect(Object.keys(eventPayload.fullData).length).toBe(2);
    expect(Object.keys(eventPayload.fullData['TestSheet2']).length).toBe(1);
    expect(Object.keys(eventPayload.fullData['Sheet1']).length).toBe(0);
    expect(eventPayload.fullData['TestSheet2'][0].Notes).toBe('This is a test note');

  });
});
