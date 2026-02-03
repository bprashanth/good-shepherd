# Fomo platform layout 

This document outlines the platform layout and how it maps to different components 
```
+-------------------------------------------------------------+
|                        App.vue                              |
|-------------------------------------------------------------|
|                                                             |
|  +-------------------------+  +--------------------------+  |
|  |                         |  |                          |  |
|  |                         |  |                          |  |
|  |      Main Content       |  |     DataViewer Panel     |  |
|  |    (via <router-view>)  |  |      (toggleable)        |  |
|  |                         |  |                          |  |
|  |                         |  |                          |  |
|  +-------------------------+  +--------------------------+  |
|                                                             |
+-------------------------------------------------------------+

Main Content (depends on route):

  - Login:
      +-----------------------------+
      |       Login View           |
      +-----------------------------+

  - Default:
      +-----------------------------+
      |        FileUpload          |
      |     + other tools...       |
      +-----------------------------+

  - Dashboard (4 quadrants):
      +----------+----------+
      | Top-Left | Top-Right|  <- Top-Right: SchemaPanel.vue
      |          | (queries)| 
      +----------+----------+
      | Bottom-L | Bottom-R |
      |          |          |
      +----------+----------+

DataViewer Panel (right side):
  - Edge toggles for:
      - "data" -> JsonViewer
      - "queries" -> Placeholder
  - NEXT button -> triggers dashboard transition
```


The DataViewer panel might be a little confusion. 
In the main page, it has 
- JsonViewer (data preview)
- ReaderMapComponent (when GeoJSON is present)
- A NEXT button that transitions to the Dashboard view

