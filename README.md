# ⚽ Query your A.I. about FIFA Soccer Rules ⚽

## Introduction
 
This repository houses a codebase that leverages NLP techniques to create an interactive chat application that answers queries about FIFA soccer rules. The code is in Python and uses Langchain and Streamlit library to create an engaging and user-friendly web application.

The core of this project is the Langchain Conversational Retrieval Chain, a sophisticated AI model that retrieves accurate answers to user queries. This model is set up on a FIFA soccer rules pdf document and can answer a wide range of questions about the game's regulations. The model's responses are accurate and provide the source documents as references for further reading.

My goal is to provide a comprehensive example of how to build an AI-powered chat application, guiding you through each step, from setting up the Streamlit session states, handling form submissions, retrieving and processing the AI responses to creating an interactive chat interface.

Whether you're a beginner just starting with NLP or an experienced developer looking for inspiration for your next project, this repository is valuable. We encourage you to explore the code, try running it on your local machine, and let us know if you have any questions or feedback. Happy coding!

## Technical environment

The technical environment for this project is built on the robust and scalable infrastructure of Azure Cloud. Each application component leverages a specific Azure service, ensuring optimal performance and seamless integration between different system parts.

The core of our application, the Large Language Model (LLM), is hosted on Azure OpenAI. 

Application also utilizes Azure Cognitive Search. I use it as a vector database, allowing application to quickly and efficiently retrieve the most relevant information in response to user queries.

Lastly, all the PDF files used as reference documents by our application are stored in Azure Blob Storage. This service allows application to store, retrieve, and link to PDF files highly efficiently and cost-effectively.

By leveraging the power of Azure Cloud, this project ensures high performance, scalability, and reliability, providing an excellent user experience and making it a robust solution for AI-powered chat applications.

## Into the code:

### .env:
This project relies on several Azure services and you'll need to provide their configuration.

Follow these steps to configure your Azure services and prepare your .env file:

- Azure OpenAI: Go to your Azure portal, and under Azure AI services, create an Azure OpenAI service. After creation, you will receive an API key and base URL, which you will fill in the following fields:
1. OPENAI_API_KEY_AZURE: Your Azure OpenAI API key
2. OPENAI.API_BASE: Your Azure OpenAI base URL
- Azure Cognitive Search Service: Create an Azure Cognitive Search Service under Azure AI services. After creation, you will get an API key, index name, and endpoint. Fill these details in the following fields:

1. AZURE_COGNITIVE_SEARCH_API_KEY: Your Azure Cognitive Search API key
2. AZURE_COGNITIVE_SEARCH_INDEX_NAME: Your Azure Cognitive Search index name
3. AZURE_COGNITIVE_SEARCH_ENDPOINT: Your Azure Cognitive Search endpoint

- Azure Storage Account: Create a new Azure Storage Account. After creation, you'll get a storage key and account name. Fill these details in the following fields:

1. AZURE_STORAGE_KEY: Your Azure Storage Account key
2. AZURE_STORAGE_ACCOUNT: Your Azure Storage Account name

- Azure PDF Container: Within your newly created Azure Storage Account, create a PDF container. Fill its name in the following field:

1. AZURE_PDF_CONTAINER: Your Azure PDF Container name
2. Replace all <-------> placeholders in your .env file with the respective keys, endpoints, and names obtained from Azure.
   
### Important notes 
Keep your .env file secure and do not commit it to your public repository. It contains sensitive data that, if exposed, can lead to unauthorized access to your Azure resources.
The OPENAI.API_TYPE and OPENAI.API_VERSION fields are pre-set to "azure" and "2023-07-01-preview", respectively. You should only change these if you are specifically instructed to do so.

### llm.py:

The llm.py file creates instances of various classes that facilitate language model operations and Azure services.
Ensure that the "gpt-35-turbo" and "text-embedding-ada-002" models are correctly configured in your Azure OpenAI service for the application to function properly.
You can opt to use a better model, such as "gpt-4", but be aware that this could significantly increase costs.

### pdf-loader.py:
 
The pdf-loader.py file is responsible for reading PDF documents from the 'docs' folder and preparing them for upload to the Azure Cognitive Search Service and Azure Storage Container. This code is adapted from an existing script in the Azure-Samples/azure-search-openai-demo repository (https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/scripts/prepdocs.py) and has been customized to work with the Langchain AzureSearch retriever.

In order to populate your vector database (Azure Cognitive Search) and Azure Blob Container with pdf file, it is necessary to execute this script.

### pdf-builder.py:

This script is used to read a PDF file and write specific pages of that file to a new PDF.


