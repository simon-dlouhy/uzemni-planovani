import os
import fitz
import tiktoken
import pandas as pd
from openai import OpenAI
from utils import chunk_prompt, analysis_prompt, summary_prompt

CHUNK_MODEL = 'gpt-3.5-turbo'
SUMMARY_MODEL = 'o4-mini'
CHUNK_TOKEN_LIMIT = 1500
ENCODER = tiktoken.encoding_for_model(CHUNK_MODEL)

def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        return '\\n'.join(page.get_text() for page in doc)
    except Exception as e:
        print(f'pdf soubor nelze přečíst: {e}')
        return ''

def split_text_into_chunks(text, max_tokens=CHUNK_TOKEN_LIMIT):
    words = text.split()
    chunks, chunk, tokens = [], [], 0
    for word in words:
        t = len(ENCODER.encode(word))
        if tokens + t > max_tokens:
            chunks.append(' '.join(chunk))
            chunk, tokens = [word], t
        else:
            chunk.append(word)
            tokens += t
    if chunk:
        chunks.append(' '.join(chunk))
    return chunks

def gpt_call(prompt, model, client):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': 'Jsi asistent v oblasti územního plánování.'},
                {'role': 'user', 'content': prompt}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f'Funkce gpt_call selhala: {e}')
        return ''

def analyze_chunk(chunk_text, client):
    prompt = chunk_prompt
    prompt += f"\\n'''\\n{chunk_text}\\n'''"
    return gpt_call(prompt, model=CHUNK_MODEL, client=client)

def summarize_issues_and_trends(all_responses, client):
    prompt = analysis_prompt
    prompt += f"\\n'''\\n{all_responses}\\n'''"
    return gpt_call(prompt, model=SUMMARY_MODEL, client=client)

def parse_summary(summary_text):
    lines = summary_text.strip().splitlines()
    problems, trends = [], []
    current = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if 'problémy' in line.lower():
            current = problems
        elif 'trendy' in line.lower():
            current = trends
        elif line.startswith('-') and current is not None:
            current.append(line.lstrip('- ').strip())
    return problems[:5], trends[:5]

def analyze_issues_and_trends(city_name: str, api_key: str, csv_path='cleansed_data/municipalities.csv') -> bool:
    client = OpenAI(api_key=api_key)

    folder = f'municipalities_data/{city_name}'
    pdf_path = os.path.join(folder, 'plan.pdf')
    output_path = os.path.join(folder, 'municipality_enriched.csv')

    if not os.path.exists(pdf_path):
        print(f'pdf soubor nebyl nalezen: {pdf_path}')
        return False

    full_text = extract_text_from_pdf(pdf_path)
    if not full_text:
        print('Z pdf souboru nebyl extrahován žádný text.')
        return False

    chunks = split_text_into_chunks(full_text)
    if not chunks:
        print('Nebyly vytvořeny žádné části textu.')
        return False

    responses = []
    for chunk in chunks:
        result = analyze_chunk(chunk, client)
        if result:
            responses.append(result)

    combined = '\\n\\n'.join(responses)
    summary = summarize_issues_and_trends(combined, client)
    problems, trends = parse_summary(summary)

    df = pd.read_csv(csv_path)
    mask = df['obec'].str.lower() == city_name.lower()

    if not mask.any():
        print(f'Obec "{city_name}" nebyla nalezena v csv souboru.')
        return False

    for i in range(5):
        column_p = f'problem_{i+1}'
        column_t = f'trend_{i+1}'

        df.loc[mask, column_p] = problems[i] if i < len(problems) else ''
        df.loc[mask, column_t] = trends[i] if i < len(trends) else ''

    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    os.makedirs(folder, exist_ok=True)
    df[mask].to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'Trendy a problémy jsou uložené zde: {output_path}')
    return True

def generate_summary_txt(city_name: str, api_key: str) -> bool:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    folder = f'municipalities_data/{city_name}'
    pdf_path = os.path.join(folder, 'plan.pdf')
    summary_txt_path = os.path.join(folder, 'specific_summary.txt')

    if not os.path.exists(pdf_path):
        print(f'pdf soubor nebyl nalezen: {pdf_path}')
        return False

    full_text = extract_text_from_pdf(pdf_path)
    if not full_text:
        print('Z pdf souboru nebyl extrahován žádný text.')
        return False

    chunks = split_text_into_chunks(full_text)
    if not chunks:
        print('Části textu nebyly vytvořeny.')
        return False
    summary_input = '\n'.join(chunks[:50])

    prompt = summary_prompt
    prompt += f"\n'''\n{summary_input}\n'''"
    summary = gpt_call(prompt, model=SUMMARY_MODEL, client=client)

    try:
        os.makedirs(folder, exist_ok=True)
        with open(summary_txt_path, 'w', encoding='utf-8') as f:
            f.write(f'Specifické shrnutí pro obec {city_name}\n\n')
            f.write(summary)
        print(f'Souhrn textové části územního plánu je uložen zde: {summary_txt_path}')
        return True
    except Exception as e:
        print(f'Shrnutí se nepodařilo uložit: {e}')
        return False

