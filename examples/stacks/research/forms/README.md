# form-viewer

This is a vue3 form-to-db viewer. The basic idea is that some forms have already been processed via a backend and those processed artifacts (json/jpeg) are available in the `assets` forlder as dependencies. These can be regenerated via different projects. 

These are the Dependencies:
* Input files in `assets/` - upload the `jpg/png` files along with corresponding `_classified.json` files. 
* To generate the `_classified.json` file, see [cloud README.md](../cloud/README.md)

For now, the form viewer just displays the jsons over the jpegs (as a tabular overlay) so people can visually see the autodetected values over the real png/jpeg form images. It also provides a correction interface to the site where users can update fields that are wrongly identified, save these updates, and then download the modified json forms. 

The output artifact of this stage will be json datasets containing the data in the forms. 

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```
