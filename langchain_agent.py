from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from scripts.summarizer import analyze_issues_and_trends, generate_summary_txt
from scripts.bigquery_updater import update_table
from scripts.downloader import download_plan
from manual_run import zip_city_folder, send_email
import os


@tool
def download_plan_tool(city_name: str) -> str:
    '''Stáhni PDF soubor územního plánu pro zadanou obec.'''
    return download_plan(city_name) or 'Stahování selhalo'

@tool
def analyze_issues_and_trends_tool(city_name: str) -> str:
    '''Analyzuj 5 hlavních problémů a trendů pro danou obec.'''
    key = os.getenv('OPENAI_API_KEY')
    result = analyze_issues_and_trends(city_name, key)
    return 'Analýza problémů a trendů dokončena' if result else 'Analýza selhala'

@tool
def generate_summary_tool(city_name: str) -> str:
    '''Vytvoř krátké shrnutí územního plánu a .txt soubor, který ho obsahuje.'''
    key = os.getenv('OPENAI_API_KEY')
    result = generate_summary_txt(city_name, key)
    return 'Shrnutí vytvořeno' if result else 'Vytvoření shrnutí selhalo'

@tool
def update_bigquery_tool(city_name: str) -> str:
    '''Aktualizuj BigQuery tabulku obohacenými daty.'''
    success = update_table(city_name)
    return 'Tabulka byla aktualizována' if success else 'Aktualizace tabulky selhala'

@tool
def zip_tool(city_name: str) -> str:
    '''Komprimuj výstupní složku pro obec do .zip souboru.'''
    return zip_city_folder(city_name)

@tool
def send_email_tool(city_name: str) -> str:
    '''Odešli zkomprimovaný výstup na zadanou e-mailovou adresu.'''
    email = os.getenv('RECIPIENT_EMAIL')
    if not email:
        return 'Nebyl nalezen e-mail příjemce.'

    zip_path = f'municipalities_data/{city_name}.zip'
    subject = f'Územní analýza: {city_name}'
    body = f'Zde jsou výstupy analytického nástroje pro obec {city_name}.'
    send_email(email, subject, body, zip_path)
    return f'E-mail byl odeslán na adresu: {email}'

def run_langchain_agent(task: str):
    llm = ChatOpenAI(model_name='gpt-4o', temperature=0)
    tools = [
        download_plan_tool,
        analyze_issues_and_trends_tool,
        generate_summary_tool,
        update_bigquery_tool,
        zip_tool,
        send_email_tool
    ]
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    result = agent.run(task)
    print(result)

if __name__ == '__main__':
    print('Agent pro územní plánování (vložte "konec" pro ukončení)\n')
    while True:
        task = input('>> Co mám udělat?\n')
        if task.lower() in ('konec', 'quit'):
            break
        run_langchain_agent(task)
