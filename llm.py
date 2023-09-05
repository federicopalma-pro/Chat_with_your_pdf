from langchain.chat_models import AzureChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import AzureSearch
from decouple import config


llm_qa = AzureChatOpenAI(
     deployment_name="gpt-35-turbo",
    model_name="gpt-35-turbo",
    openai_api_version=config('OPENAI.API_VERSION'),
    openai_api_key=config('OPENAI_API_KEY_AZURE'),
    openai_api_base=config('OPENAI.API_BASE'),
    temperature=0,
    max_tokens=1024,
    n=1
)


llm_condense = AzureChatOpenAI(
    deployment_name="gpt-35-turbo",
    model_name="gpt-35-turbo",
    openai_api_version=config('OPENAI.API_VERSION'),
    openai_api_key=config('OPENAI_API_KEY_AZURE'),
    openai_api_base=config('OPENAI.API_BASE'),
    temperature=0,
    max_tokens=1024,
    n=1
)

embeddings = OpenAIEmbeddings(
    deployment="embedding",
    model="text-embedding-ada-002",
    openai_api_version=config('OPENAI.API_VERSION'),
    openai_api_key=config('OPENAI_API_KEY_AZURE'),
    openai_api_base=config('OPENAI.API_BASE'),
    openai_api_type=config('OPENAI.API_TYPE')
)


acs = AzureSearch(
    azure_search_endpoint=config('AZURE_COGNITIVE_SEARCH_ENDPOINT'),
    azure_search_key=config('AZURE_COGNITIVE_SEARCH_KEY'),
    index_name=config('AZURE_COGNITIVE_SEARCH_INDEX_NAME'),
    embedding_function=embeddings.embed_query,
    search_type="hybrid"
)
