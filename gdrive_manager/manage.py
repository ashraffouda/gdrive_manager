from __future__ import print_function
from googleapiclient import discovery
import googleapiclient
from httplib2 import Http
from oauth2client import file, client, tools
import click
import io
from googleapiclient.http import MediaIoBaseDownload


# G docs files can not be downloaded directly should be exported
GDOCS_TYPES = {
    "application/vnd.google-apps.document": {
        "target": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ext": ".docx",
        "type": "docs",
    },
    "application/vnd.google-apps.drawing": {
        "target": "image/png",
        "ext": ".png",
        "type": "drawings",
    },
    "application/vnd.google-apps.presentation": {
        "target": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "ext": ".pptx",
        "type": "slides",
    },
    "application/vnd.google-apps.spreadsheet": {
        "target": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ext": ".xlsx",
        "type": "spreadsheets",
    },
}

def _get_service(cred):
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    store = file.Storage("storage.json")
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(cred, SCOPES)
        creds = tools.run_flow(flow, store)
    return discovery.build("drive", "v3", http=creds.authorize(Http()))

@click.group()
@click.pass_context
def cli(ctx):
    pass

def _build_query(doc_type, only_docs, include_trashed):
    query = []
    if doc_type == "pdf":
        query.append(f"mimeType='application/pdf'")
    elif doc_type != "all":
        for k, v in GDOCS_TYPES.items():
            if v["type"] == doc_type:
                query.append(f"mimeType='{k}'")
                break
        else:
            raise Exception(f"Can not find docs for specified type: {doc_type}")
    elif only_docs:
        for k in GDOCS_TYPES.keys():
            query.append(f"mimeType='{k}'")
    query = ' or '.join(query)
    if not include_trashed:
        query += "and trashed=false"
    print(f"QUERY: {query}")
    return query

@cli.command()
@click.option(
    "--cred", default="./credentials.json", help="Path to your Google API credentials"
)
@click.option(
    "--doc-type",
    type=click.Choice(["docs", "slides", "drawings", "spreadsheets", "all"]),
    default="all",
    help="type of documents you want to download",
)
@click.option("--only-docs", is_flag=True, help="Only download google docs files")
@click.option("--include-trashed", is_flag=True, help="Include trashed files")
def clean_perms(cred, only_docs, doc_type, include_trashed):
    service = _get_service(cred)
    query = _build_query(doc_type, only_docs, include_trashed)
    files = service.files().list(q=query).execute().get("files", [])
    files_ids = map(lambda x: x["id"], files)
    for file_id in files_ids:
        file_perms = (
            service.permissions().list(fileId=file_id).execute().get("permissions", [])
        )
        for file_perm in file_perms:
            if file_perm["id"] == "anyoneWithLink":
                service.permissions().delete(
                    fileId=file_id, permissionId=file_perm["id"]
                ).execute()


def _is_confirmed(question):
    while True:
        reply = str(input(question + " (y/n): ")).lower().strip()
        if reply[:1] == "y":
            return True
        if reply[:1] == "n":
            return False


@cli.command()
@click.option("--prefix", default="._", help="prefix of files you want to delete")
@click.option(
    "--cred", default="./credentials.json", help="Path to your Google API credentials"
)
@click.option("--force", is_flag=True, help="force delete without confirmation")
@click.option(
    "--doc-type",
    type=click.Choice(["docs", "slides", "drawings", "spreadsheets", "all"]),
    default="all",
    help="type of documents you want to download",
)
@click.option("--only-docs", is_flag=True, help="Only download google docs files")
@click.option("--include-trashed", is_flag=True, help="Include trashed files")
def delete_items(prefix, cred, force, only_docs, doc_type, include_trashed):
    service = _get_service(cred)
    query = _build_query(doc_type, only_docs, include_trashed)
    files = service.files().list(q=query).execute().get("files", [])
    for f in files:
        if f["name"].startswith(prefix):
            try:
                if not force:
                    if not _is_confirmed(
                        f"Are you sure you want to delete file `{f['name']}`"
                    ):
                        continue
                service.files().delete(fileId=f["id"]).execute()
            except googleapiclient.errors.HttpError as error:
                if error.resp["status"] == "404":
                    pass
                else:
                    print(error.content.decode())


def _download_file(request, _file, ext, base_dir):
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        _, done = downloader.next_chunk()
        print(f"Downloading file: {_file['name']}.")
    with open(f"{base_dir}/{_file['name']}{ext}", "wb") as f:
        f.write(fh.getbuffer())


@cli.command()
@click.option(
    "--cred", default="./credentials.json", help="Path to your Google API credentials"
)
@click.option(
    "--base-dir", default="/tmp", help="destination to where files will be downloaded"
)
@click.option(
    "--download-type",
    type=click.Choice(["orig", "pdf", "both"]),
    default="pdf",
    help="download type for google docs",
)
@click.option(
    "--doc-type",
    type=click.Choice(["docs", "slides", "drawings", "spreadsheets", "pdf", "all"]),
    default="all",
    help="type of documents you want to download",
)
@click.option("--only-docs", is_flag=True, help="Only download google docs files")
@click.option("--include-trashed", is_flag=True, help="Include trashed files")
def download_items(cred, base_dir, download_type, doc_type, only_docs, include_trashed):
    service = _get_service(cred)
    query = _build_query(doc_type, only_docs, include_trashed)
    files = service.files().list(q=query).execute().get("files", [])
    for f in files:
        try:
            print(f"Downloading file:{f}... ")
            if f["mimeType"] == "application/vnd.google-apps.folder":
                continue
            if f["mimeType"] in GDOCS_TYPES:
                if download_type == "orig":
                    request = service.files().export_media(
                        fileId=f["id"], mimeType=GDOCS_TYPES[f["mimeType"]]["target"]
                    )
                    _download_file(
                        request, f, GDOCS_TYPES[f["mimeType"]]["ext"], base_dir
                    )
                elif download_type == "pdf":
                    request = service.files().export_media(
                        fileId=f["id"], mimeType="application/pdf"
                    )
                    _download_file(request, f, "pdf", base_dir)
                elif download_type == "both":
                    request = service.files().export_media(
                        fileId=f["id"], mimeType=GDOCS_TYPES[f["mimeType"]]["target"]
                    )
                    _download_file(
                        request, f, GDOCS_TYPES[f["mimeType"]]["ext"], base_dir
                    )
                    request = service.files().export_media(
                        fileId=f["id"], mimeType="application/pdf"
                    )
                    _download_file(request, f, "pdf", base_dir)
            else:
                request = service.files().get_media(fileId=f["id"])
                _download_file(request, f, "", base_dir)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    cli()
