from __future__ import print_function
from googleapiclient import discovery
import googleapiclient
from httplib2 import Http
from oauth2client import file, client, tools
import click

@click.group()
@click.pass_context
def cli(ctx):
    pass

@cli.command()
@click.option("--cred", default="./credentials.json", help="Path to your Google API credentials")
def clean_perms(dir, cred):
    SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file"]
    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(cred, SCOPES)
        creds = tools.run_flow(flow, store)
    service = discovery.build('drive', 'v3', http=creds.authorize(Http()))
    files = service.files().list().execute().get('files', [])
    files_ids = map(lambda x: x["id"], files)
    for file_id in files_ids:
        file_perms = service.permissions().list(fileId=file_id).execute().get("permissions",[])
        for file_perm in file_perms:
            if file_perm["id"] == "anyoneWithLink":
                service.permissions().delete(fileId=file_id, permissionId=file_perm['id']).execute()

def is_confirmed(question):
    while True:
        reply = str(input(question+' (y/n): ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False
@cli.command()
@click.option("--prefix", default="._", help="prefix of files you want to delete")
@click.option("--cred", default="./my_account_credentials.json", help="Path to your Google API credentials")
@click.option('--force', is_flag=True, help="force delete without confirmation")
def delete_items(prefix, cred, force):
    SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/drive.file"]
    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(cred, SCOPES)
        creds = tools.run_flow(flow, store)
    service = discovery.build('drive', 'v3', http=creds.authorize(Http()))
    files=service.files().list().execute().get('files', [])
    for f in files:
        if f["name"].startswith(prefix):
            try:
                if not force:
                    if not is_confirmed(f"Are you sure you want to delete file `{f['name']}`"):
                        continue
                service.files().delete(fileId=f['id']).execute()
            except googleapiclient.errors.HttpError as error:
                if error.resp['status'] == "404":
                    pass
                else:
                    print(error.content.decode())


if __name__ == "__main__":
    cli()
