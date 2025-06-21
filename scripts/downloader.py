import os
import pandas as pd
import requests

def download_plan(city_name: str,
                  csv_path='cleansed_data/municipalities_links.csv',
                  output_dir='municipalities_data') -> str | None:
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f'Nepovedlo se načíst CSV soubor: {e}')
        return None

    match = df[df['obec'].str.lower() == city_name.lower()]
    if match.empty:
        print(f'Obec "{city_name}" nebyla nalezena v CSV souboru.')
        return None

    url = match.iloc[0]['url'].strip('{}')
    city_folder = os.path.join(output_dir, city_name)
    os.makedirs(city_folder, exist_ok=True)
    file_path = os.path.join(city_folder, 'plan.pdf')

    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f'Územní plán byl stažen do adresáře: {file_path}')
        return file_path
    except Exception as e:
        print(f'Nepovedlo se stáhnout soubor: {e}')
        return None
