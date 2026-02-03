
/*
 * The key used to store user query templates in local storage.
 */
const STORAGE_KEY = 'userQueryTemplates';


// A known set of placeholders that can be used in the templates.
export const PLACEHOLDER_ENUMS = {
  SITENAME: 'sitename',
  USERNAME: 'username',
  TIMESTAMP: 'timestamp',
  SPECIES: 'species',
  LATITUDE: 'latitude',
  LONGITUDE: 'longitude',
  SPECIESNAME: 'speciesname',
};

export const PLACEHOLDER_PATTERNS = {
  SITENAME: ['sitename', 'site', 'siteid', 'site_id', 'site-id', 'site_name', 'site-name', 'name',  'siteName', 'location', 'loc', 'stationId', 'station_id'],
  USERNAME: ['username', 'user', 'userid', 'user_id', 'user-id', 'user_name', 'user-name', 'person', 'person_name'],
  TIMESTAMP: ['timestamp', 'time', 'date', 'datetime', 'created_at', 'updated_at', 'time_stamp', 'date_time', 'createdAt', 'updatedAt'],
  SPECIES: ['species', 'animal', 'wildlife', 'fauna', 'taxon', 'taxonomy', 'species_name', 'animal_name', 'wildlife_name'],
  LATITUDE: ['lat', 'latitude'],
  LONGITUDE: ['lng', 'longitude', 'long'],
};

/*
 * The templates to use to resolve natural language queries.
 *
 * @param {string} id: A unique identifier for the template.
 * @param {string} targetPanel: The panel to target with the template.
 * @param {string} mode: Currently "replace" is the only mode, meaning replace
 *    the contents of the panel with the output of the template computation.
 * @param {string} pattern: The pattern to use to match the template.
 * @param {string} label: The human readable label to use for the template.
 * @param {function} extract: The function to use to extract the value from the
 *    match.
 * @param {string} sqlTemplate: The SQL template to use for the template.
 * @param {string[]} placeholders: The placeholders used within the human
 *    readable label. These placeholders are typically replaced with the values
 *    of the data in the panel (eg sitename <-> "hulibanda") through a modal.
 */
const defaultTemplates = [
    {
      // TODO(prashanth@): Make these match patterns more specific. Currently
      // this will catch both "show me huli data " and "show me huli data for
      // the last 30 days" under the same query.
      id: "showSiteData",
      pattern: /show me (.+) data/i,
      label: 'Show me <sitename> data',
      targetPanel: 'schema',
      mode: 'replace',
      extract: (match) => match[1],
      sqlTemplate: "SELECT * FROM ? WHERE <sitename_key> LIKE '%<sitename_value>%'",
      placeholders: [PLACEHOLDER_ENUMS.SITENAME]
    },
    {
      id: "timelapseImages",
      pattern: /create a timelapse of images in site (.+)/i,
      label: 'Create a timelapse of images in site <sitename>',
      targetPanel: 'image',
      mode: 'replace',
      extract: (match) => match[1],
      sqlTemplate: "SELECT * FROM ? WHERE <sitename_key> = '<sitename_value>' ORDER BY <timestamp_key>",
      placeholders: [PLACEHOLDER_ENUMS.SITENAME]
    },
    {
      id: "showUserData",
      label: "Show data for user <username>",
      targetPanel: "schema",
      mode: "replace",
      sqlTemplate: "SELECT * FROM ? WHERE <username_key> = '<username_value>'",
      placeholders: [PLACEHOLDER_ENUMS.USERNAME]
    },
    {
      id: "showAllSites",
      label: "Show all sites on map",
      targetPanel: "map",
      mode: "overlay",
      sqlTemplate: "SELECT latitude, longitude, siteId FROM ? WHERE latitude IS NOT NULL"
    }
  ];

/**
 * Save a user query to local storage.
 *
 * This function appends to the list returned by getUserQueries.
 *
 * @param {Object} template - The template to save, eg:
 * {
 *   label: 'My Query',
 *   sqlTemplate: 'SELECT * FROM ? WHERE username = 'foo' ORDER BY date'
 * }
 */
function saveUserQuery(template) {
  const current = getUserQueries();
  // TODO(prashanth@): Add fields to the new template like id, targetPanel,
  // mode, etc.
  current.push(template);
  console.log('QueryTemplateService: saveUserQuery: len(current): ', current.length);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(current));
}

/**
 * Delete a user query from local storage.
 *
 * @param {string} label - The label of the query to delete.
 */
function deleteUserQuery(label) {
  const current = getUserQueries();
  const newCurrent = current.filter(template => template.label !== label);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newCurrent));
}

/**
 * Get all user queries from local storage.
 *
 * When there are no queies, return a list. The idea is that saveUserQuery
 * adds to this list and re-sets the STORAGE_KEY.
 *
 * @returns {Array} The user queries.
 */
function getUserQueries() {
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? JSON.parse(raw) : [];
}

export {
  saveUserQuery,
  deleteUserQuery,
  getUserQueries,
  defaultTemplates
};