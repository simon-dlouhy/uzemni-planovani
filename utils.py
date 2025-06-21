from google.cloud import bigquery
import pandas as pd
import os
import numpy as np

chunk_prompt = f'''
Jsi odborník na územní a krajinné plánování. Na základě následující části územního plánu identifikuj:

- Maximálně 3 konkrétní problémy, každý nejvýše 8 slov.
- Maximálně 3 konkrétní rozvojové trendy, každý nejvýše 8 slov.

Nepřidávej komentáře. Výstup uveď jako dva seznamy s odrážkami. Zaměř se na rozvoj území a strategickou koncepci obce. Dále se zabývej zejména charakterem území, jeho vymezením a specifiky související s územním rozvojem v dané obci.

Část plánu:
'''

analysis_prompt = f'''
Jsi analytik územního plánování. Na základě následujících výstupů z územního plánu obce vytvoř:

- Seznam 5 hlavních problémů (max 8 slov, bez duplicit).
- Seznam 5 hlavních trendů (max 8 slov, bez duplicit).

Výstup uveď jako dva seznamy s odrážkami nadepsané jako hlavní problémy nebo hlavní trendy. Zaměř se na rozvoj území a strategickou koncepci obce. Dále se zabývej zejména charakterem území, jeho vymezením a specifiky souvisejícími s územním rozvojem v dané obci.

Výstupy z analýzy:
'''

summary_prompt = f'''
Na základě následujícího textu z územního plánu obce napiš krátké shrnutí (maximálně 140 slov), které zdůrazní specifika a jedinečné charakteristiky plánování v této konkrétní obci. Zaměř se na rozvoj území a strategickou koncepci obce. Dále se zabývej zejména charakterem území, jeho vymezením a specifiky souvisejícími s územním rozvojem v dané obci.

Text plánu:
'''

int_cols = [
    'municipality_kod',
    'pou_kod',
    'okres_kod',
    'pocet_obyvatel_2023', 
    'prirozeny_prirustek_2023', 
    'prirustek_stehovanim_2023',
    'obyvatele_0_14_2023', 
    'obyvatele_15_64_2023', 
    'obyvatele_65_2023', 
    'dokoncene_byty_2023', 
    'ubytovaci_zarizeni_2023',
    'narozeni_2023', 
    'zemreli_2023', 
    'pristehovali_2023', 
    'vystehovali_2023',
    'pocet_obyvatel_2022', 
    'prirozeny_prirustek_2022', 
    'prirustek_stehovanim_2022',
    'obyvatele_0_14_2022', 
    'obyvatele_15_64_2022', 
    'obyvatele_65_2022',
    'dokoncene_byty_2022', 
    'ubytovaci_zarizeni_2022',
    'narozeni_2022', 
    'zemreli_2022', 
    'pristehovali_2022', 
    'vystehovali_2022'
]

float_cols = [
    'prijmy_2023', 
    'vydaje_2023', 
    'nezamestnanost_2023', 
    'zemedelska_puda_2023', 
    'nezemedelska_puda_2023',
    'prumerny_vek_2023',
    'koeficient_ekologie_2023', 
    'prijmy_2022', 
    'vydaje_2022', 
    'nezamestnanost_2022', 
    'zemedelska_puda_2022', 
    'nezemedelska_puda_2022',
    'prumerny_vek_2022',
    'koeficient_ekologie_2022',
]

str_cols = [
    'obec', 
    'kraj', 
    'url',
    'posledni_dokumentace',
    'posledni_dokumentace_datum',
    'trend_1', 
    'trend_2',
    'trend_3', 
    'trend_4', 
    'trend_5', 
    'problem_1', 
    'problem_2',
    'problem_3',
    'problem_4',
    'problem_5',
]

schema = [
    bigquery.SchemaField('obec', 'STRING'),
    bigquery.SchemaField('kraj', 'STRING'),
    bigquery.SchemaField('url', 'STRING'),
    bigquery.SchemaField('municipality_kod', 'INTEGER'),
    bigquery.SchemaField('pou_kod', 'INTEGER'),
    bigquery.SchemaField('okres_kod', 'INTEGER'),
    bigquery.SchemaField('pocet_obyvatel_2023', 'INTEGER'),
    bigquery.SchemaField('prirozeny_prirustek_2023', 'INTEGER'),
    bigquery.SchemaField('prirustek_stehovanim_2023', 'INTEGER'),
    bigquery.SchemaField('obyvatele_0_14_2023', 'INTEGER'),
    bigquery.SchemaField('obyvatele_15_64_2023', 'INTEGER'),
    bigquery.SchemaField('obyvatele_65_2023', 'INTEGER'),
    bigquery.SchemaField('prijmy_2023', 'FLOAT'),
    bigquery.SchemaField('vydaje_2023', 'FLOAT'),
    bigquery.SchemaField('dokoncene_byty_2023', 'INTEGER'),
    bigquery.SchemaField('ubytovaci_zarizeni_2023', 'INTEGER'),
    bigquery.SchemaField('nezamestnanost_2023', 'FLOAT'),
    bigquery.SchemaField('narozeni_2023', 'INTEGER'),
    bigquery.SchemaField('zemreli_2023', 'INTEGER'),
    bigquery.SchemaField('pristehovali_2023', 'INTEGER'),
    bigquery.SchemaField('vystehovali_2023', 'INTEGER'),
    bigquery.SchemaField('zemedelska_puda_2023', 'FLOAT'),
    bigquery.SchemaField('nezemedelska_puda_2023', 'FLOAT'),
    bigquery.SchemaField('koeficient_ekologie_2023', 'FLOAT'),
    bigquery.SchemaField('prumerny_vek_2023', 'FLOAT'),
    bigquery.SchemaField('pocet_obyvatel_2022', 'INTEGER'),
    bigquery.SchemaField('prirozeny_prirustek_2022', 'INTEGER'),
    bigquery.SchemaField('prirustek_stehovanim_2022', 'INTEGER'),
    bigquery.SchemaField('obyvatele_0_14_2022', 'INTEGER'),
    bigquery.SchemaField('obyvatele_15_64_2022', 'INTEGER'),
    bigquery.SchemaField('obyvatele_65_2022', 'INTEGER'),
    bigquery.SchemaField('prijmy_2022', 'FLOAT'),
    bigquery.SchemaField('vydaje_2022', 'FLOAT'),
    bigquery.SchemaField('dokoncene_byty_2022', 'INTEGER'),
    bigquery.SchemaField('ubytovaci_zarizeni_2022', 'INTEGER'),
    bigquery.SchemaField('nezamestnanost_2022', 'FLOAT'),
    bigquery.SchemaField('narozeni_2022', 'INTEGER'),
    bigquery.SchemaField('zemreli_2022', 'INTEGER'),
    bigquery.SchemaField('pristehovali_2022', 'INTEGER'),
    bigquery.SchemaField('vystehovali_2022', 'INTEGER'),
    bigquery.SchemaField('zemedelska_puda_2022', 'FLOAT'),
    bigquery.SchemaField('nezemedelska_puda_2022', 'FLOAT'),
    bigquery.SchemaField('koeficient_ekologie_2022', 'FLOAT'),
    bigquery.SchemaField('prumerny_vek_2022', 'FLOAT'),
    bigquery.SchemaField('posledni_dokumentace', 'STRING'),
    bigquery.SchemaField('posledni_dokumentace_datum', 'STRING'),
    bigquery.SchemaField('trend_1', 'STRING'),
    bigquery.SchemaField('trend_2', 'STRING'),
    bigquery.SchemaField('trend_3', 'STRING'),
    bigquery.SchemaField('trend_4', 'STRING'),
    bigquery.SchemaField('trend_5', 'STRING'),
    bigquery.SchemaField('problem_1', 'STRING'),
    bigquery.SchemaField('problem_2', 'STRING'),
    bigquery.SchemaField('problem_3', 'STRING'),
    bigquery.SchemaField('problem_4', 'STRING'),
    bigquery.SchemaField('problem_5', 'STRING'),
]
