from typing import List, Dict
from embedding_pipeline.vector_db import VectorDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_recipes_by_keywords(keywords: List[str], limit: int = 3) -> List[Dict]:
    """
    Search for recipes using a list of ingredients.
    
    Args:
        keywords (List[str]): List of ingredients to search for (e.g., ['chicken', 'tomato', 'onion'])
        limit (int): Maximum number of recipes to return
        
    Returns:
        List[Dict]: List of recipes matching the ingredients, sorted by relevance
    """
    try:
        # Initialize the vector database connection
        vector_db = VectorDB()
        
        # Combine keywords into a search term
        search_term = ' '.join(keywords)
        
        # Search for similar recipes
        results = vector_db.find_similar_recipes(search_term, limit)
        
        # Close the database connection
        vector_db.close()
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching recipes: {str(e)}")
        raise

# Example usage
if __name__ == "__main__":
    # Example search with ingredients
    ingredients = ["pasta", "onions", "tomato"]
    recipes = search_recipes_by_keywords(ingredients)
    
    # Print results
    for i, recipe in enumerate(recipes, 1):
        print(f"\nRecipe {i}:")
        print(f"Name: {recipe['RecipeName']}")
        print(f"Cooking Time: {recipe['TimeToCook']}")
        print(f"Ingredients: {recipe['Ingredients']}")
        print(f"Instructions: {recipe['Instructions']}")
        print(f"Similarity Score: {recipe['similarity']:.4f}")
