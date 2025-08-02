import pandas as pd
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        
    def get_processed_data(self) -> Tuple[List[str], List[Dict]]:
        """Process the recipe data from CSV and return texts for embeddings and full metadata.

        Returns:
            Tuple[List[str], List[Dict]]: List of recipe texts and their full metadata.
        """
        try:
            df = pd.read_csv(self.csv_path)
            
            # Create the text for embedding generation
            # Use all relevant fields to create a rich text representation
            recipe_texts = df.apply(
                lambda row: f"Recipe: {row.get('RecipeName', '')}. "
                           f"Ingredients: {row.get('Ingredients', '')}. "
                           f"TimeToCook: {row.get('TimeToCook', '')}. "
                           f"Instructions: {row.get('Instructions', '')}",
                axis=1
            ).tolist()

            # Keep ALL original columns as metadata
            # The vector_db will select the necessary columns for insertion
            metadata = df.to_dict('records')
            
            logger.info(f"Successfully processed {len(df)} recipes. Metadata includes all original columns.")
            return recipe_texts, metadata
        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            raise 
        
