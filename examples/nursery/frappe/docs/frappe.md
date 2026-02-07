# Documenting some internals on frappe

1. Sites vs Apps: sites are instances of apps. Apps are the code and standards etc defining a site. 

2. Modules: are just ways to organize doctypes in the sidebar. Namespaces etc. 

3. Doctypes: are APIs within modules. 

4. Placing doctypes eg nursery: 

Frappe expects exactly this: 
```
{bench}/apps/{app_name}/{app_name}/{module_name}/doctype/{doctype_name}
```
`bench new-app nurser` creates 3 things 
* A directory aka the git repo for the app. It contains a license, readme etc for _that_ app. This is located at `frappe-bench/apps/nursery`
* The python package which frappe can import. This contains some logic, in `frappe-bench/apps/nursery/nursery/`
* The default module. This is just named after the app for simplicity, but we can create other modules. This is the *third* `nursery` in the path `frappe-bench/apps/nursery/nursery/nursery`
* The doctype is created via `bench new-doctype` and goes within the module directory. 
* Logic for when to create a new module: core app goes in `nursery`. Everything that's a primitive of the app lives in the default module. 

5. Links are basically foreign keys. Eg in Batch, the species field is a Link to Species; in Event, batch links to Batch.

6. Workspaces are nothing but landing pages or dashboards that have shortcuts and links to other `module->doctypes`
7. Search: Frappe auto fuzzy matches based on `search_fields` mentioned in the doctype
	- also via indexed fields 
8. Child  tables: data that belongs to a certain form and no where else (duplicated everywhere else, edits are not transmitted)
	- non searchable doctypes
	- auto cascade delete on parent delete 
	- one-to-many
	- main disadvantage is basically these aren't "searchable" in the standard way. We need to convert them into hidden indices during validation.
9. Autoname functions: run before validate and used as a hook to generate names. 
```
save -> autoname -> validate -> insert 
```

10. Custom query/reports: depending on their nature they could be ui logic, sql queries or py/js scripts stored in the app. But the overall goal is to filter and render doctypes. Reports are aggregated into dashboards that are just a collection of pointers with big numbers - these are directly embedded in the workspace. 

* Script reports holds logic for computation 
* Dashboard charts hold graphs themselves 
	- static filters per chart with `filter_json`
* The js just chooses what filters to show on the page 

11. Custom js: matched to doctypes, just like custom validation logic one can add js logic that autofills 

12. List view: fields that should be shown in the list view (i.e. better than a random hash id)

## Other doubts 

* Sections: are all sections "available" for all stages? meaning i can have batch 1 in stage germination and batch 2 in stage growing, both in section 1 bed 1? 
* Movement: is bed enough to mark movement?
	- is "move" event enough to get something from germination to growth? 
	- do we need section name and stage? 
* Height: is min/max ht of batch enough? 
* Algorithm for short name generation? is 3,3 enough, and will we need fuzzy search on local names? 
	- append sequence number on collision
	- always allow user edit
* Local Name/dialect search: serach batch based on it, search species based on it
* Do we need guardrails? possible errors: wrong batch (wrong conceptual thing), wrong physical location (section/bed etc), wrong measurement (height, germinatoin count etc). 
