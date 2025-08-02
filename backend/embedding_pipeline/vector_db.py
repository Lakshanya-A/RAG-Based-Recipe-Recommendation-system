import os #file operations
from typing import List, Dict, Optional #type hints
import logging #logging
from dotenv import load_dotenv #parse environment variables
import singlestoredb as s2 #singlestore database
import torch #pytorch
import re #regular expressions
import json
import math #for checking NaN values
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self):
        """
        Initialize the vector database connection using environment variables.
        """
        load_dotenv()
        
        connection_string = os.getenv('SINGLESTORE_CONNECTION_STRING')
        if not connection_string:
            raise ValueError("SINGLESTORE_CONNECTION_STRING not found in environment variables")
            
        try:
            # Using client_side_local_infile=True might be needed depending on setup
            self.conn = s2.connect(connection_string)
            logger.info("Connected to SingleStore database")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def create_tables(self):
        """
        Create necessary tables for storing recipe data and embeddings.
        """
        cursor = self.conn.cursor()
        
        # Drop existing table if it exists to update schema
        cursor.execute("DROP TABLE IF EXISTS recipes")
        
        # Create recipes table with correct vector dimension
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipes (
                id INT PRIMARY KEY,
                RecipeName VARCHAR(255),
                TimeToCook VARCHAR(50),
                Ingredients TEXT,
                Instructions TEXT,
                embedding VECTOR(768)
            )
        """)
        
        self.conn.commit()
        logger.info("Created necessary tables with 768-dimensional vector support")
        
    def insert_recipes(self, recipes: List[Dict], batch_size: int = 50):
        """
        Insert recipes into the database in batches using parameterized queries.
        
        Args:
            recipes (List[Dict]): List of recipes with their embeddings and metadata
            batch_size (int): Number of recipes to insert in each batch
        """
        with self.conn.cursor() as cursor:
            insert_sql = """
            INSERT INTO recipes (id, RecipeName, TimeToCook, Ingredients, Instructions, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            # Process in batches
            for i in range(0, len(recipes), batch_size):
                batch = recipes[i:i + batch_size]
                logger.info(f"Inserting batch {i//batch_size + 1}/{(len(recipes) + batch_size - 1)//batch_size}")
                
                # Prepare the data for the batch
                batch_data = []
                for recipe in batch:
                    try:
                        # Check for NaN values in embedding and replace with 0
                        embedding = recipe.get('embedding', [])
                        if isinstance(embedding, list):
                            # Replace any NaN values with 0
                            embedding = [0.0 if isinstance(x, float) and math.isnan(x) else x for x in embedding]
                        
                        # Convert embedding to JSON array string
                        embedding_json = json.dumps(embedding)
                        
                        # Prepare tuple of values in correct order
                        # Note: Need to handle potential KeyError if a column is missing in the scraped data
                        recipe_values = (
                            recipe.get('id'),
                            recipe.get('RecipeName'),
                            recipe.get('TimeToCook'),
                            recipe.get('Ingredients'),
                            recipe.get('Instructions'),
                            embedding_json # Pass the JSON string for the vector column
                        )
                        batch_data.append(recipe_values)
                    except Exception as e:
                        logger.error(f"Error preparing data for recipe {recipe.get('id', 'unknown')}: {str(e)}")
                        # Skip this recipe if data preparation fails
                        continue
                
                if not batch_data:
                    logger.warning(f"No valid data to insert in batch {i//batch_size + 1}")
                    continue
                
                # Execute the batch insert
                try:
                    # Use executemany for efficient batch insertion
                    cursor.executemany(insert_sql, batch_data)
                    self.conn.commit()
                    logger.info(f"Successfully inserted batch {i//batch_size + 1}")
                except Exception as e:
                    logger.error(f"Error inserting batch {i//batch_size + 1}: {str(e)}")
                    self.conn.rollback()
                    # Note: Retrying with smaller batches is harder with executemany,
                    # if a batch fails, you might need to log the problematic recipes
                    # or implement more complex retry logic.
                    # For simplicity, we just log and continue to the next batch.
                
            logger.info(f"Completed insertion process.")
        
    def find_similar_recipes(self, search_term: str, limit: int = 2) -> List[Dict]:
        """
        Find recipes similar to the given search term using vector similarity search.
        
        Args:
            search_term (str): The search term (e.g., "chicken" or "pasta")
            limit (int: Maximum number of results to return (default: 2)
            
        Returns:
            List[Dict]: List of recipes matching the search term
        """
        try:
            cursor = self.conn.cursor()
            
            # First check if we have any recipes in the database
            cursor.execute("SELECT COUNT(*) FROM recipes")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.warning("No recipes found in the database")
                return []
            
            # Split the search term into individual ingredients
            ingredients = [i.strip().lower() for i in search_term.split(',') if i.strip()]
            
            if not ingredients:
                logger.warning("No valid ingredients provided in the search term")
                return []
            
            # Construct the WHERE clause dynamically for each ingredient
            where_clauses = ["LOWER(Ingredients) LIKE %s" for _ in ingredients]
            where_clause_str = " OR ".join(where_clauses)
            
            # Simple query to find recipes containing any of the search terms
            query = f"""
                SELECT 
                    RecipeName,
                    TimeToCook,
                    Ingredients,
                    Instructions
                FROM recipes
                WHERE {where_clause_str}
                LIMIT %s
            """
            
            # Prepare parameters for the query
            params = [f'%{ingredient}%' for ingredient in ingredients]
            params.append(limit)
            
            # Execute the query with parameters
            cursor.execute(query, params)
            
            results = cursor.fetchall()
            
            if not results:
                logger.warning(f"No recipes found matching: '{search_term}'")
                return []
            
            # Convert results to list of dictionaries
            similar_recipes = []
            for row in results:
                try:
                    recipe = {
                        'RecipeName': row[0],
                        'TimeToCook': row[1],
                        'Ingredients': row[2],
                        'Instructions': row[3],
                        'similarity': 1.0  # Simple matching, so similarity is 1.0
                    }
                    similar_recipes.append(recipe)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Error processing recipe row: {str(e)}")
                    continue
            
            logger.info(f"Found {len(similar_recipes)} recipes matching: '{search_term}'")
            return similar_recipes
            
        except Exception as e:
            logger.error(f"Error finding similar recipes: {str(e)}")
            raise

    def close(self):
        """
        Close the database connection.
        """
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

class CookingAssistant:
    def __init__(self, vector_db: 'VectorDB'):
        """
        Initialize the cooking assistant with VectorDB.
        """
        load_dotenv()
        
        self.vector_db = vector_db
        self.user_preferences = {
            'dietary_restrictions': [],
            'cooking_skill_level': 'intermediate',
            'preferred_cuisines': [],
            'last_recipe': None
        }

    def process_message(self, message: str) -> str:
        """
        Process a user message and return an appropriate response.
        This version directly uses the Gemini API for content generation.
        """
        try:
            import google.generativeai as genai # Corrected import statement
            load_dotenv()
            # Use the user's provided API usage example
            api_key=os.getenv('GEMINI_API_KEY')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            prompt = (message +" You are a helpful recipe recommender assistant. Answer only if the question is relevant to the recipe recommendations, food based, time to cook, where the dish is most famous etc. all and only about food. If the question is not relevant to food, say 'I'm sorry, I can only help with recipe recommendations.'. Give answers in the format: Recipe name, Time to cook, Ingredients, Instructions. Give no extra information unless asked for.")
            response = model.generate_content(prompt)
            
            if hasattr(response, "text") and response.text:
                return response.text
            else:
                return "I apologize, but I couldn't generate a response for your query. Please try again."
            
        except Exception as e:
            logger.error(f"Error generating response with Gemini API: {str(e)}")
            return "I apologize, but I encountered an error while trying to generate a response. Please ensure your GEMINI_API_KEY is correct and try again."


print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

#  # import google.genai as genai # Corrected import statement
#             load_dotenv()
#             # Use the user's provided API usage example
#             client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
#             response = client.models.generate_content(
#                 model="gemini-2.0-flash", contents=message + "You are a helpful recipe recommender assistant. Answer only if the question is relevant to the recipe recommendations, food based, time to cook, where the dish is most famous etc. all and only about food. If the question is not relevant to food, say 'I'm sorry, I can only help with recipe recommendations.'. Give answers in the format: Recipe name, Time to cook, Ingredients, Instructions. Give no extra information unless asked for"
#             )
            
#             if response and response.text:
#                 return response.text
#             else:
#                 return "I apologize, but I couldn't generate a response for your query. Please try again."
