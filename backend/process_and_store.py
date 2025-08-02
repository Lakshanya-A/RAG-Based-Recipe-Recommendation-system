# this file is used to process the data and store it in the database, it is used to create the database and insert the data into it.4
import os
from embedding_pipeline.data_processor import DataProcessor
from embedding_pipeline.embedding_generator import EmbeddingGenerator
from embedding_pipeline.vector_db import VectorDB
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize components
    data_processor = DataProcessor('../data_scrape/recipes.csv')
    embedding_generator = EmbeddingGenerator()
    vector_db = VectorDB()
    
    try:
        # Process data
        logger.info("Starting data processing pipeline")
        recipe_texts, metadata = data_processor.get_processed_data()
        
        # Generate embeddings
        logger.info("Generating embeddings")
        processed_recipes = embedding_generator.process_recipes(recipe_texts, metadata)
        
        # Store in database
        logger.info("Storing in database")
        vector_db.create_tables()
        vector_db.insert_recipes(processed_recipes)
        
        logger.info("Successfully completed data processing and storage")
        
    except Exception as e:
        logger.error(f"Error in processing pipeline: {str(e)}")
        raise
    finally:
        vector_db.close()

if __name__ == "__main__":
    main() 
