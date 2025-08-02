import requests as req
from bs4 import BeautifulSoup
import pandas as pd

base_url = "https://www.food.com"
main_url = "https://www.food.com/ideas/top-dessert-recipes-6930?ref=nav#c-791390"
# https://www.food.com/ideas/indian-food-recipes-at-home-6821?ref=nav#c-877755
# https://www.food.com/ideas/top-dessert-recipes-6930?ref=nav#c-791390
# https://www.food.com/ideas/easy-lunch-recipes-7007?ref=nav#c-821312

# get the recipe links from the main page
html_text = req.get(main_url)
soup = BeautifulSoup(html_text.text, 'html.parser')

title_divs = soup.find_all('h2', class_='title')

recipe_links = []
recipe_names = []
for div in title_divs:
    anchor = div.find('a')
    if anchor:
        recipe_name = anchor.text.strip()
        recipe_url = base_url + anchor['href'] if anchor['href'].startswith('/') else anchor['href'] + '?units=metric&scale=3'
        recipe_links.append(recipe_url)
        recipe_names.append(recipe_name)

recipes_data = []

for recipe_name, link in zip(recipe_names, recipe_links):
    html_text = req.get(link)
    soup = BeautifulSoup(html_text.text, 'html.parser')

    # Ingredients
    ingredients_list = soup.find('ul', class_='ingredient-list')
    ingredients = []
    if ingredients_list:
        for li in ingredients_list.find_all('li', recursive=False):
            ingredient_span = li.find('span', class_='ingredient-text')
            if ingredient_span:
                ingredient_link = ingredient_span.find('a')
                if ingredient_link:
                    ingredient_name = ingredient_link.text.strip()
                else:
                    ingredient_name = ingredient_span.text.strip()
            else:
                ingredient_name = ''
            if ingredient_name:
                ingredients.append(ingredient_name)
    ingredients_str = ", ".join(ingredients)

    # Instructions
    instructions = []
    directions_list = soup.find('ul', class_='direction-list')
    if directions_list:
        for step in directions_list.find_all('li', class_='direction'):
            step_text = step.get_text(strip=True)
            if step_text:
                instructions.append(step_text)
    instructions_str = " ".join(instructions)

    # Time to cook
    time_to_cook = ""
    facts_items = soup.find_all('div', class_='facts__item')
    for item in facts_items:
        label = item.find('dt', class_='facts__label')
        value = item.find('dd', class_='facts__value')
        if label and value and "Ready In:" in label.text:
            time_to_cook = value.text.strip()
            break

    recipes_data.append({
        "RecipeName": recipe_name,
        "TimeToCook": time_to_cook,
        "Ingredients": ingredients_str,
        "Instructions": instructions_str
    })

# Save to CSV
df = pd.DataFrame(recipes_data)
df.to_csv("recipes_dessert.csv", index=False)
print("Saved recipes to recipes_dessert.csv")
