## How to use
1- download GoogleDriveAPI credentials from [here](https://developers.google.com/drive/api/v3/quickstart/python) to the root dir next to this readme
click on `Enable the drive api`

2- install dependecies using poetry
```
poetry install
```

3- entry poetry shell
```
poetry shell
```
4- to clean permissions use 
```
python gdrive_manager/manage.py clean-perms 
```
5- to clean files and folders
```
python gdrive_manager/manage.py delete-items 
```
* you can specify `--force` incase you want to automatically delete files without confirmation
* also `--prefix` to delete all files/folder with the specified prefix default is `._`
6- Downloading files
```
python  gdrive_manager/manage.py download-items --base-dir=/tmp/bak --only-docs --download-type=orig
```
* --base dir Base dir to download files to

# Options that applies to all commands
* --only-docs if specified will only get google-docs(docs, spreadsheets, slides and drawings)
* --doc-type=<type> choose one of google-docs-types
* --include-trashed if specified will include trashed files
