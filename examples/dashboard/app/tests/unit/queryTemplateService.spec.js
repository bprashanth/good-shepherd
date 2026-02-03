import { describe, test, expect } from "vitest";
import { resolveNaturalLanguageQuery } from "@/services/queryTemplateService";

const mockData = [
  { species: "tiger_white", year: 2023, image_url: "img1.jpg", timestamp: "2023-04-01" },
  { species: "elephant", year: 2022, image_url: "img2.jpg", timestamp: "2022-04-01" },
  { site_name: "periyar", image_url: "img3.jpg", timestamp: "2023-05-01" }
];

describe("resolveNaturalLanguageQuery", () => {
  test("resolves 'show me tiger data' to a SQL LIKE query", () => {
    const input = "show me tiger data";
    const expected = "SELECT * FROM ? WHERE species LIKE '%tiger%'";
    const result = resolveNaturalLanguageQuery(input, mockData);
    expect(result).toBe(expected);
  });

  test("resolves 'create a timelapse of images in site periyar'", () => {
    const input = "create a timelapse of images in site periyar";
    const expected = "SELECT image_url, timestamp FROM ? WHERE site_name = 'periyar' ORDER BY timestamp";
    const result = resolveNaturalLanguageQuery(input, mockData);
    expect(result).toBe(expected);
  });

  test("returns null if no template matches", () => {
    const input = "unknown query that should not match";
    const result = resolveNaturalLanguageQuery(input, mockData);
    expect(result).toBe(null);
  });

  test("returns null if no matching key found in data", () => {
    const input = "show me pangolin data"; // no pangolin in mockData
    const result = resolveNaturalLanguageQuery(input, mockData);
    expect(result).toBe(null);
  });
});

