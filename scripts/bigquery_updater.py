from google.cloud import bigquery
import pandas as pd
import os
import numpy as np
from utils import int_cols, float_cols, str_cols, schema

def enforce_column_types(df, int_cols, float_cols, str_cols):
    for col in int_cols:
        df[col] = df[col].replace('', np.nan).astype('Int64')

    for col in float_cols:
        df[col] = df[col].replace('', np.nan).astype(float)

    for col in str_cols:
        df[col] = df[col].astype(str)
    
    return df

def update_table(city_name: str,
                          creds='google_credentials.json',
                          project_id='landscape-planning-agent',
                          dataset_id='landscape_planning',
                          table_id='municipalities') -> bool:
    try:
        csv_path = f'municipalities_data/{city_name}/municipality_enriched.csv'
        if not os.path.exists(csv_path):
            print(f'Soubor nebyl nalezen {csv_path}')
            return False

        df = pd.read_csv(csv_path)
        df = enforce_column_types(df, int_cols, float_cols, str_cols)
        client = bigquery.Client.from_service_account_json(creds, project=project_id)

        temp_table = f'{table_id}_temp'
        temp = f'{project_id}.{dataset_id}.{temp_table}'

        job = bigquery.LoadJobConfig(
            schema=schema,
            write_disposition='WRITE_TRUNCATE'
        )

        load_job = client.load_table_from_dataframe(df, temp, job_config=job)
        load_job.result()

        merge_sql = f'''
        MERGE `{project_id}.{dataset_id}.{table_id}` T
        USING `{temp}` S
        ON T.municipality_kod = S.municipality_kod
        WHEN MATCHED THEN UPDATE SET
            {', '.join([f'T.{col} = S.{col}' for col in df.columns if col != 'municipality_kod'])}
        WHEN NOT MATCHED THEN INSERT ROW
        '''

        client.query(merge_sql).result()
        client.delete_table(temp, not_found_ok=True)

        print(f'Tabulka v BigQuery byla aktualizovaná pro obec: {city_name}')
        return True

    except Exception as e:
        print(f'Aktualizace v BigQuery selhala: {e}')
        return False
