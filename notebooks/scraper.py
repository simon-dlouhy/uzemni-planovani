import requests
import os
import pandas as pd

csu = 'https://csu.gov.cz/docs/107516/eab39014-0cbe-286f-46ae-d02abadcee8c/uap_obce.xlsx?version=2.0'
uur = 'https://eupc.uur.cz/api/Dokumentace/PrehledAkciExport'
dir = os.path.join(os.path.dirname(__file__), '../data_sources')

output_csu_xlsx = os.path.join(dir, 'csu_obce.xlsx')
outputs_csu_csv = {
    'obce 2023': os.path.join(dir, 'stat_obce_2023.csv'),
    'obce 2022': os.path.join(dir, 'stat_obce_2022.csv')
}
output_uur = 'uur_data.xlsx'

uur_header = {
    'Content-Type': 'application/json',
    'Origin': 'https://eupc.uur.cz',
    'Referer': 'https://eupc.uur.cz/dokumentaceakcesestava',
    'User-Agent': 'Mozilla/5.0'
}
uur_payload = {
    'kategorieKod': 'LAS',
    'kraj': '',
    'katUze': '',
    'okres': '',
    'orp': '',
    'dokumentaceDruh': [99, 102],
    'akce': [106, 108, 107, 117, 112, 115, 114, 116, 113, 105, 104, 103, 101],
    'akceDatum': '',
    'datum': None,
    'operace': 1
}

os.makedirs(dir, exist_ok=True)

def download_csu():
    r = requests.get(csu)
    r.raise_for_status()
    with open(output_csu_xlsx, 'wb') as f:
        f.write(r.content)

    for sheet_name, output_path in outputs_csu_csv.items():
        df = pd.read_excel(output_csu_xlsx, sheet_name=sheet_name, skiprows=4, engine='openpyxl')
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f'Soubor byl uložen {output_path}')

def download_uur():
    response = requests.post(uur, json=uur_payload, headers=uur_header)
    response.raise_for_status()
    save_path_uur = os.path.join(dir, output_uur)
    with open(save_path_uur, 'wb') as f:
        f.write(response.content)
    uur_df = pd.read_excel(save_path_uur, engine='openpyxl')
    save_path_uur_csv = os.path.join(dir, 'uur_data.csv')
    uur_df.to_csv(save_path_uur_csv, index=False, encoding='utf-8-sig')

    print(f'Soubor byl uložen {save_path_uur_csv}')

if __name__ == '__main__':
    download_csu()
    download_uur()


