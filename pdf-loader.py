import openai
import os
import io
import re
import html
import base64
import json
from decouple import config
from pypdf import PdfReader, PdfWriter
from azure.storage.blob import BlobServiceClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswParameters,
    PrioritizedFields,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticSettings,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
)
from tenacity import retry, stop_after_attempt, wait_random_exponential

MAX_SECTION_LENGTH = 1000
SENTENCE_SEARCH_LIMIT = 100
SECTION_OVERLAP = 100

# Setup
pdf_category = "soccer"
cognitive_search_index = config('AZURE_COGNITIVE_SEARCH_INDEX_NAME')
pdf_container = config('AZURE_PDF_CONTAINER')
storageaccount = config('AZURE_STORAGE_ACCOUNT')

storage_creds = config('AZURE_STORAGE_KEY')
openai.api_type = config('OPENAI.API_TYPE')
openai.api_base = config('OPENAI.API_BASE')
openai.api_version = config('OPENAI.API_VERSION')
openai.api_key = config('OPENAI_API_KEY_AZURE')
cognitive_search_endpoint = config('AZURE_COGNITIVE_SEARCH_ENDPOINT')
cognitive_search_key = config('AZURE_COGNITIVE_SEARCH_KEY')

index_client = SearchIndexClient(endpoint=cognitive_search_endpoint,
                                 credential=AzureKeyCredential(cognitive_search_key))
search_client = SearchClient(endpoint=cognitive_search_endpoint,
                             credential=AzureKeyCredential(
                                 cognitive_search_key),
                             index_name=cognitive_search_index)


def blob_name_from_file_page_blob(filename, page=0):
    if os.path.splitext(filename)[1].lower() == ".pdf":
        return os.path.splitext(os.path.basename(filename))[0] + f"-{page}" + ".pdf"
    else:
        return os.path.basename(filename)


def blob_name_from_file_page(filename, category, page=0):
    data = {
        "document": filename,
        "page": page,
        "category": category
    }
    json_data = json.dumps(data)
    return json_data


def upload_blobs(filename, storageaccount, container):
    blob_service = BlobServiceClient(
        account_url=f"https://{storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(container)
    if not blob_container.exists():
        blob_container.create_container()

    # if file is PDF split into pages and upload each page as a separate blob
    if os.path.splitext(filename)[1].lower() == ".pdf":
        reader = PdfReader(filename)
        pages = reader.pages
        for i in range(len(pages)):
            blob_name = blob_name_from_file_page_blob(filename, i)
            f = io.BytesIO()
            writer = PdfWriter()
            writer.add_page(pages[i])
            writer.write(f)
            f.seek(0)
            blob_container.upload_blob(blob_name, f, overwrite=True)
    else:
        blob_name = blob_name_from_file_page_blob(filename)
        with open(filename, "rb") as data:
            blob_container.upload_blob(blob_name, data, overwrite=True)


def remove_blobs(filename, storageaccount, container):
    blob_service = BlobServiceClient(
        account_url=f"https://{storageaccount}.blob.core.windows.net", credential=storage_creds)
    blob_container = blob_service.get_container_client(container)
    if blob_container.exists():
        if filename is None:
            blobs = blob_container.list_blob_names()
        else:
            prefix = os.path.splitext(os.path.basename(filename))[0]
            blobs = filter(lambda b: re.match(f"{prefix}-\d+\.pdf", b), blob_container.list_blob_names(
                name_starts_with=os.path.splitext(os.path.basename(prefix))[0]))
        for b in blobs:
            blob_container.delete_blob(b)


def table_to_html(table):
    table_html = "<table>"
    rows = [sorted([cell for cell in table.cells if cell.row_index == i],
                   key=lambda cell: cell.column_index) for i in range(table.row_count)]
    for row_cells in rows:
        table_html += "<tr>"
        for cell in row_cells:
            tag = "th" if (
                cell.kind == "columnHeader" or cell.kind == "rowHeader") else "td"
            cell_spans = ""
            if cell.column_span > 1:
                cell_spans += f" colSpan={cell.column_span}"
            if cell.row_span > 1:
                cell_spans += f" rowSpan={cell.row_span}"
            table_html += f"<{tag}{cell_spans}>{html.escape(cell.content)}</{tag}>"
        table_html += "</tr>"
    table_html += "</table>"
    return table_html


def get_document_text(filename):
    offset = 0
    page_map = []
    reader = PdfReader(filename)
    pages = reader.pages
    for page_num, p in enumerate(pages):
        page_text = p.extract_text()
        page_map.append((page_num, offset, page_text))
        offset += len(page_text)

    return page_map


def split_text(page_map):
    SENTENCE_ENDINGS = [".", "!", "?"]
    WORDS_BREAKS = [",", ";", ":", " ",
                    "(", ")", "[", "]", "{", "}", "\t", "\n"]

    def find_page(offset):
        num_pages = len(page_map)
        for i in range(num_pages - 1):
            if offset >= page_map[i][1] and offset < page_map[i + 1][1]:
                return i
        return num_pages - 1

    all_text = "".join(p[2] for p in page_map)
    length = len(all_text)
    start = 0
    end = length
    while start + SECTION_OVERLAP < length:
        last_word = -1
        end = start + MAX_SECTION_LENGTH

        if end > length:
            end = length
        else:
            # Try to find the end of the sentence
            while end < length and (end - start - MAX_SECTION_LENGTH) < SENTENCE_SEARCH_LIMIT and all_text[end] not in SENTENCE_ENDINGS:
                if all_text[end] in WORDS_BREAKS:
                    last_word = end
                end += 1
            if end < length and all_text[end] not in SENTENCE_ENDINGS and last_word > 0:
                end = last_word  # Fall back to at least keeping a whole word
        if end < length:
            end += 1

        # Try to find the start of the sentence or at least a whole word boundary
        last_word = -1
        while start > 0 and start > end - MAX_SECTION_LENGTH - 2 * SENTENCE_SEARCH_LIMIT and all_text[start] not in SENTENCE_ENDINGS:
            if all_text[start] in WORDS_BREAKS:
                last_word = start
            start -= 1
        if all_text[start] not in SENTENCE_ENDINGS and last_word > 0:
            start = last_word
        if start > 0:
            start += 1

        section_text = all_text[start:end]
        yield (section_text, find_page(start))

        last_table_start = section_text.rfind("<table")
        if (last_table_start > 2 * SENTENCE_SEARCH_LIMIT and last_table_start > section_text.rfind("</table")):
            # If the section ends with an unclosed table, we need to start the next section with the table.
            # If table starts inside SENTENCE_SEARCH_LIMIT, we ignore it, as that will cause an infinite loop for tables longer than MAX_SECTION_LENGTH
            # If last table starts inside SECTION_OVERLAP, keep overlapping
            # if args.verbose: print(f"Section ends with unclosed table, starting next section with the table at page {find_page(start)} offset {start} table start {last_table_start}")
            start = min(end - SECTION_OVERLAP, start + last_table_start)
        else:
            start = end - SECTION_OVERLAP

    if start + SECTION_OVERLAP < end:
        yield (all_text[start:end], find_page(start))


def filename_to_id(filename):
    filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", filename)
    filename_hash = base64.b16encode(filename.encode('utf-8')).decode('ascii')
    return f"file-{filename_ascii}-{filename_hash}"


def create_sections(filename, page_map):
    file_id = filename_to_id(filename)
    for i, (content, pagenum) in enumerate(split_text(page_map)):
        section = {
            "id": f"{file_id}-page-{i}",
            "content": content,
            "metadata": blob_name_from_file_page(filename, pdf_category, pagenum),
            "content_vector": compute_embedding(content)
        }
        yield section


def before_retry_sleep(retry_state):
    print("Rate limited on the OpenAI embeddings API, sleeping before retrying...")


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(15), before_sleep=before_retry_sleep)
def compute_embedding(text):
    return openai.Embedding.create(engine="embedding", input=text)["data"][0]["embedding"]


def create_search_index(index):
    if index not in index_client.list_index_names():
        index = SearchIndex(
            name=index,
            fields=[
                SimpleField(name="id", type="Edm.String", key=True,
                            ilterable=True, filterable=True),
                SearchableField(name="content", type="Edm.String",
                                analyzer_name="en.microsoft"),
                SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                            hidden=False, searchable=True, filterable=False, sortable=False, facetable=False,
                            vector_search_dimensions=1536, vector_search_configuration="default"),
                SearchableField(name="metadata", type="Edm.String",
                                analyzer_name="en.microsoft")
            ],
            semantic_settings=SemanticSettings(
                configurations=[SemanticConfiguration(
                    name='default',
                    prioritized_fields=PrioritizedFields(
                        title_field=None, prioritized_content_fields=[SemanticField(field_name='content')]))]),
            vector_search=VectorSearch(
                algorithm_configurations=[
                    VectorSearchAlgorithmConfiguration(
                        name="default",
                        kind="hnsw",
                        hnsw_parameters=HnswParameters(metric="cosine")
                    )
                ]
            )
        )
        print(f"Creating {index} search index")
        index_client.create_index(index)
    else:
        print(f"Search index {index} already exists")


def index_sections(filename, sections):
    i = 0
    batch = []
    for s in sections:
        batch.append(s)
        i += 1
        if i % 1000 == 0:
            results = search_client.upload_documents(documents=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")


# ----------- Setup upload docs --------------------------------------------
file_name = os.listdir("docs")
file_pdf = [file for file in file_name if file.lower().endswith(".pdf")]

# ---------- Upload to Azure Container PDF files spit per pages -------------
for pdf_filename in file_pdf:
    upload_blobs(filename=("docs\\" + pdf_filename), storageaccount=storageaccount,
                 container=pdf_category)

# ---------- Create Azure Cognitive Search index ----------------------------
create_search_index(index=cognitive_search_index)

# ---------- Load documents to Azure Cognitive Search
for pdf_filename in file_pdf:
    page_map = get_document_text("docs\\" + pdf_filename)
    sections = create_sections(filename=pdf_filename, page_map=page_map)
    index_sections(pdf_filename, sections)

# ------------ Remove pdf file from azure container --------------------------
# remove_blobs(filename="<------->", storageaccount=storageaccount, container="<------->")
