from textwrap import dedent
from typing import Optional, List, Dict, Any
import json
import os

from agno.agent import Agent
from agno.embedder.openai import OpenAIEmbedder
from agno.knowledge.csv import CSVKnowledgeBase
from agno.memory.v2.db.postgres import PostgresMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat
from agno.storage.agent.postgres import PostgresAgentStorage
from agno.tools.googlesheets import GoogleSheetsTools
from agno.tools.toolkit import Toolkit
from agno.tools.file import FileTools
from agno.vectordb.pgvector import PgVector, SearchType

from db.session import db_url


def get_product_csv_knowledge() -> CSVKnowledgeBase:
    """Create CSV knowledge base for product data"""
    return CSVKnowledgeBase(
        path="data/product_csv",  # Directory where CSV files will be stored
        vector_db=PgVector(
            db_url=db_url,
            table_name="product_image_csv_knowledge",
            search_type=SearchType.hybrid,
            embedder=OpenAIEmbedder(id="text-embedding-3-small"),
        ),
        num_documents=10  # Return top 10 matches when searching
    )


class ProductImageSearchTools(Toolkit):
    """Custom toolkit for product image search with Serper API"""
    
    def __init__(self):
        super().__init__(name="product_image_search_tools")
        self.api_key = "7eb754e913754229bd81b68109a9e5139342c334"
        self.last_search_results = None  # Store last search results
        self.register(self.search_product_images)
        self.register(self.get_results_for_sheets)
        self.register(self.process_csv_for_knowledge)
    
    async def search_product_images(self, brand: str, product: str, product_id: str = None, category: str = None) -> str:
        """
        Search for product images using Serper API and return formatted results.
        
        Args:
            brand: Brand name
            product: Product name
            product_id: Optional product ID
            category: Optional category
            
        Returns:
            Formatted search results for display
        """
        import aiohttp
        
        # Construct search query
        search_query = f"{brand} {product}".strip()
        
        # Prepare search parameters
        search_params = {
            "q": search_query,
            "type": "images",
            "tbs": "qdr:y",  # Recent images from past year
            "engine": "google",
            "num": 10
        }
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://google.serper.dev/images",
                    json=search_params,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract relevant fields from results
                    results = []
                    if "images" in data:
                        for img in data["images"][:10]:
                            results.append({
                                "title": img.get("title", ""),
                                "imageUrl": img.get("imageUrl", ""),
                                "source": img.get("source", ""),
                                "brand": brand,
                                "product": product,
                                "product_id": product_id,
                                "category": category
                            })
                    
                    search_results = {
                        "query": search_query,
                        "results": results,
                        "count": len(results)
                    }
                    self.last_search_results = search_results  # Store for later use
                    
                    # Format and return results
                    return self.format_results_for_display(search_results)
                    
        except Exception as e:
            error_msg = f"Error searching images: {str(e)}"
            self.last_search_results = {
                "error": error_msg,
                "query": search_query,
                "results": []
            }
            return error_msg
    
    def format_results_for_display(self, search_results: Dict[str, Any]) -> str:
        """Format search results for chat display"""
        if "error" in search_results:
            return search_results["error"]
        
        if not search_results.get("results"):
            return "No image results found for the search query."
        
        output = f"Found {search_results['count']} images for '{search_results['query']}':\n\n"
        
        for i, result in enumerate(search_results["results"], 1):
            output += f"**Result {i}:**\n"
            output += f"- Title: {result['title']}\n"
            output += f"- Image URL: {result['imageUrl']}\n"
            output += f"- Source: {result['source']}\n\n"
        
        return output
    
    def get_results_for_sheets(self, num_results: int = 10) -> List[List[str]]:
        """
        Get the last search results formatted for Google Sheets output.
        
        Args:
            num_results: Number of results to return (1-10)
            
        Returns:
            List of rows for Google Sheets
        """
        if not self.last_search_results:
            return [["No search results available. Please perform a search first."]]
        
        if "error" in self.last_search_results:
            return [[self.last_search_results["error"]]]
        
        rows = []
        if "results" in self.last_search_results:
            for result in self.last_search_results["results"][:num_results]:
                row = [
                    result.get("brand", ""),
                    result.get("product", ""),
                    result.get("product_id", ""),
                    result.get("category", ""),
                    result.get("imageUrl", ""),
                    result.get("source", ""),
                    result.get("title", "")
                ]
                rows.append(row)
        
        return rows
    
    async def process_csv_for_knowledge(self, csv_file_path: str) -> str:
        """
        Process a CSV file and add it to the knowledge base.
        
        Args:
            csv_file_path: Path to the CSV file
            
        Returns:
            Status message
        """
        import os
        import shutil
        
        try:
            # Create the data directory if it doesn't exist
            os.makedirs("data/product_csv", exist_ok=True)
            
            # Copy the CSV file to the knowledge base directory
            filename = os.path.basename(csv_file_path)
            dest_path = os.path.join("data/product_csv", filename)
            shutil.copy2(csv_file_path, dest_path)
            
            # The knowledge base will automatically pick up the new file
            # when search_knowledge_base is called
            
            return f"Successfully added {filename} to the product knowledge base. You can now search for products from this file."
            
        except Exception as e:
            return f"Error processing CSV file: {str(e)}"


def get_product_image_agent(
    model_id: str = "gpt-4.1",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
) -> Agent:
    # Google Sheets IDs
    output_sheet_id = "1vcwjTZldbHAJGrESm6zRndywpAArBY3V-mFxU0K8SAk"
    input_sheet_id = "11oE8bEyPEcbGC6x_plhjloZ87mf6pnnTC62tlsUuC5M"
    
    # Create tools
    product_search_tools = ProductImageSearchTools()
    
    # Google Sheets tools for both input and output
    input_sheets_tool = GoogleSheetsTools(
        spreadsheet_id=input_sheet_id
    )
    
    output_sheets_tool = GoogleSheetsTools(
        spreadsheet_id=output_sheet_id
    )
    
    # File tools for CSV handling
    file_tools = FileTools()
    
    return Agent(
        name="Product Image Search Agent",
        agent_id="product_image_agent",
        user_id=user_id,
        session_id=session_id,
        model=OpenAIChat(id=model_id),
        # Tools available to the agent
        tools=[product_search_tools, input_sheets_tool, output_sheets_tool, file_tools],
        # Knowledge base for CSV files
        knowledge=get_product_csv_knowledge(),
        # Give the agent a tool to search the knowledge base
        search_knowledge=True,
        # Description of the agent
        description=dedent("""\
            You are a Product Image Search Agent specialized in finding product images using the Serper API.
            
            Your goal is to help users find relevant product images based on brand and product information,
            and optionally output results to Google Sheets.
        """),
        # Instructions for the agent
        instructions=dedent(f"""\
            As a Product Image Search Agent, you help users find product images using various input methods.
            
            ## Input Methods:
            1. **Direct User Input**: Ask for brand, product name, and optionally product_id and category
            2. **Google Sheets Input**: Read from the input sheet (ID: {input_sheet_id})
               - Columns: brand, product, product_id, category
            3. **CSV File Upload**: Process uploaded CSV files with the same column structure
            4. **CSV Knowledge Base**: Search the knowledge base for product information
               - Use `search_knowledge_base` to find products from previously loaded CSV files
               - The knowledge base stores product data for quick retrieval
            
            ## Search Process:
            1. Combine brand and product name for the search query (e.g., "Wyld Gummy")
            2. Use the `search_product_images` function to find and display images
            3. Results are automatically formatted showing title, imageUrl, and source for up to 10 images
            
            ## Output Options:
            1. **Chat Display**: The search results are automatically shown when you call `search_product_images`
            2. **Google Sheets Output** (ID: {output_sheet_id}):
               - Ask user how many results they want (1-10)
               - Use `get_results_for_sheets` to get formatted data
               - Write to sheets with columns: brand, product, product_id, category, imageUrl, source, title
            
            ## Workflow:
            1. Determine input source (user, sheets, CSV file, or knowledge base)
            2. Gather product information:
               - For CSV uploads: Use FileTools to read the file and process rows
               - For knowledge base: Use search_knowledge_base to find products
            3. Perform image search using search_product_images
            4. Ask user for output preference (chat or sheets)
            5. Format and deliver results accordingly
            
            ## CSV Knowledge Base Management:
            - When users upload CSV files, they are automatically added to the knowledge base
            - The knowledge base persists across sessions for quick product lookups
            - CSV files should have headers: brand, product, product_id, category
            
            ## Best Practices:
            - Always use recent images (past year) for relevance
            - Include all available information in searches
            - Clearly present options to users
            - Handle errors gracefully
            
            Additional Information:
            - You are interacting with the user_id: {{current_user_id}}
            - The user's name might be different from the user_id, you may ask for it if needed and add it to your memory if they share it with you.\
        """),
        # This makes `current_user_id` available in the instructions
        add_state_in_messages=True,
        # -*- Storage -*-
        # Storage chat history and session state in a Postgres table
        storage=PostgresAgentStorage(table_name="product_image_agent_sessions", db_url=db_url),
        # -*- History -*-
        # Send the last 3 messages from the chat history
        add_history_to_messages=True,
        num_history_runs=3,
        # Add a tool to read the chat history if needed
        read_chat_history=True,
        # -*- Memory -*-
        # Enable agentic memory where the Agent can personalize responses to the user
        memory=Memory(
            model=OpenAIChat(id=model_id),
            db=PostgresMemoryDb(table_name="user_memories", db_url=db_url),
            delete_memories=True,
            clear_memories=True,
        ),
        enable_agentic_memory=True,
        # -*- Other settings -*-
        # Format responses using markdown
        markdown=True,
        # Add the current date and time to the instructions
        add_datetime_to_instructions=True,
        # Show debug logs
        debug_mode=debug_mode,
    )