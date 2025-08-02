import requests #make API requests
from typing import List, Dict #type hints
import numpy as np #numerical operations
import logging #logging
from tqdm import tqdm #progress bar
import time #time operations
import os #file operations
from dotenv import load_dotenv #parse environment variables
from requests.exceptions import RequestException #request exceptions
import json #json operations
import pickle #pickle operations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self, model_name: str = 'BAAI/bge-base-en-v1.5'):
        """
        Initialize the embedding generator with HuggingFace API.
        """
        # Load environment variables
        load_dotenv()
        
        self.model = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        
        # Get and verify token
        self.token = os.getenv('HF_TOKEN')
        logger.info(f"Token found: {'Yes' if self.token else 'No'}")
        if not self.token:
            raise ValueError("HF_TOKEN not found in environment variables. Please add it to your .env file")
            
        self.headers = {"Authorization": f"Bearer {self.token}"}
        logger.info(f"Initialized embedding generator with model: {model_name}")
        
        # Create checkpoint directory if it doesn't exist
        self.checkpoint_dir = "checkpoints"
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        
    def _make_api_request(self, texts: List[str], max_retries: int = 5) -> List:
        """
        Make API request with retry logic.
        
        Args:
            texts (List[str]): List of texts to process
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            List: Embeddings for the texts
        """
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json={"inputs": texts}
                )
                
                if response.status_code == 503:
                    # Model is loading
                    wait_time = 20
                    logger.info(f"Model is loading, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                if response.status_code == 429:
                    # Rate limit hit
                    wait_time = 30
                    logger.info(f"Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                if response.status_code == 500:
                    # Internal server error
                    wait_time = 30 * (attempt + 1)
                    logger.warning(f"Server error, retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except RequestException as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 10 * (attempt + 1)
                logger.warning(f"Request failed, retrying in {wait_time} seconds... Error: {str(e)}")
                time.sleep(wait_time)
    
    def _save_checkpoint(self, batch_index: int, embeddings: List, metadata: List[Dict]):
        """Save progress to checkpoint file."""
        checkpoint = {
            'batch_index': batch_index,
            'embeddings': embeddings,
            'metadata': metadata
        }
        with open(os.path.join(self.checkpoint_dir, 'embedding_checkpoint.pkl'), 'wb') as f:
            pickle.dump(checkpoint, f)
        logger.info(f"Saved checkpoint at batch {batch_index}")
    
    def _load_checkpoint(self) -> tuple:
        """Load progress from checkpoint file."""
        checkpoint_path = os.path.join(self.checkpoint_dir, 'embedding_checkpoint.pkl')
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path, 'rb') as f:
                checkpoint = pickle.load(f)
            logger.info(f"Loaded checkpoint from batch {checkpoint['batch_index']}")
            return checkpoint['batch_index'], checkpoint['embeddings'], checkpoint['metadata']
        return 0, [], []
        
    def generate_embeddings(self, texts: List[str], metadata: List[Dict], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a list of texts using HuggingFace API.
        
        Args:
            texts (List[str]): List of texts to generate embeddings for
            metadata (List[Dict]): List of recipe metadata
            batch_size (int): Batch size for processing
            
        Returns:
            np.ndarray: Array of embeddings
        """
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        # Load checkpoint if exists
        start_batch, all_embeddings, processed_metadata = self._load_checkpoint()
        
        # Process in batches
        for i in tqdm(range(start_batch * batch_size, len(texts), batch_size), desc="Generating embeddings"):
            batch_texts = texts[i:i + batch_size]
            batch_metadata = metadata[i:i + batch_size]
            
            try:
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                batch_embeddings = self._make_api_request(batch_texts)
                all_embeddings.extend(batch_embeddings)
                processed_metadata.extend(batch_metadata)
                
                # Save checkpoint every 5 batches
                if (i//batch_size) % 5 == 0:
                    self._save_checkpoint(i//batch_size, all_embeddings, processed_metadata)
                
                # Add a small delay between batches
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i}: {str(e)}")
                # Save checkpoint before raising error
                self._save_checkpoint(i//batch_size, all_embeddings, processed_metadata)
                raise
                
        embeddings = np.array(all_embeddings)
        logger.info(f"Generated embeddings with shape: {embeddings.shape}")
        return embeddings, processed_metadata
    
    def process_recipes(self, recipe_texts: List[str], metadata: List[Dict], batch_size: int = 32) -> List[Dict]:
        """
        Process recipes by generating embeddings and combining with metadata.
        
        Args:
            recipe_texts (List[str]): List of recipe texts
            metadata (List[Dict]): List of recipe metadata
            batch_size (int): Batch size for processing
            
        Returns:
            List[Dict]: List of recipes with their embeddings and metadata
        """
        embeddings, processed_metadata = self.generate_embeddings(recipe_texts, metadata, batch_size)
        
        processed_recipes = []
        for i, (text, meta, embedding) in enumerate(zip(recipe_texts, processed_metadata, embeddings)):
            # Split the text into RecipeName and Instructions
            parts = text.split(' ', 1)
            recipe_name = parts[0]
            instructions = parts[1] if len(parts) > 1 else ''
            
            processed_recipe = {
                'id': i,
                'RecipeName': recipe_name,
                'Instructions': instructions,
                'embedding': embedding.tolist(),
                **meta
            }
            processed_recipes.append(processed_recipe)
            
        logger.info(f"Processed {len(processed_recipes)} recipes with embeddings")
        return processed_recipes
