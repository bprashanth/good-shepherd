const { resolveNaturalLanguageQuery } = require('./src/services/queryTemplateService');

// Test data with various field naming patterns
const testData = [
  {
    site_name: "test_site",
    image_url: "https://example.com/image1.jpg",
    capture_date: "2023-01-01"
  },
  {
    site_name: "test_site",
    image_url: "https://example.com/image2.jpg",
    capture_date: "2023-01-02"
  }
];

// Test cases
const testCases = [
  {
    query: "show me test_site data",
    expected: "SELECT * FROM ? WHERE site_name LIKE '%test_site%'"
  },
  {
    query: "create a timelapse of images in site test_site",
    expected: "SELECT image_url, capture_date FROM ? WHERE site_name = 'test_site' ORDER BY capture_date"
  }
];

console.log("Testing query template resolution...\n");

testCases.forEach((testCase, index) => {
  console.log(`Test ${index + 1}: "${testCase.query}"`);
  const result = resolveNaturalLanguageQuery(testCase.query, testData);
  console.log(`Result: ${result}`);
  console.log(`Expected: ${testCase.expected}`);
  console.log(`Match: ${result === testCase.expected ? '✓' : '✗'}`);
  console.log('');
});
