import os
import shutil
import smtplib
from email.message import EmailMessage
from scripts.downloader import download_plan
from scripts.summarizer import analyze_issues_and_trends, generate_summary_txt
from scripts.bigquery_updater import update_table
from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

def zip_city_folder(city_name: str) -> str:
    folder_path = os.path.join('municipalities_data', city_name)
    zip_path = f'{folder_path}.zip'
    shutil.make_archive(folder_path, 'zip', folder_path)
    return zip_path

def send_email(recipient: str, subject: str, body: str, attachment_path: str) -> None:
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = recipient
    msg.set_content(body)

    with open(attachment_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='zip', filename=os.path.basename(attachment_path))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)

    print(f'Email byl odeslán na adresu: {recipient}')

def run_pipeline(city_name: str, recipient_email: str):
    print(f'Nástroj byl spuštěn pro obec {city_name}')

    path = download_plan(city_name)
    if not path:
        return print('Stahování plánu selhalo.')

    if not analyze_issues_and_trends(city_name, OPENAI_API_KEY):
        return print('Analýza trendů selhala.')

    if not generate_summary_txt(city_name, OPENAI_API_KEY):
        return print('Tvorba shrnutí selhala.')

    if not update_table(city_name):
        return print('Aktualizace v BigQuery selhala.')

    zip_path = zip_city_folder(city_name)
    subject = f'Územní analýza: {city_name}'
    body = f'Zde je výstupní balíček pro obec {city_name}, včetně dashboardu, PDF a obohacených dat.'
    send_email(recipient_email, subject, body, zip_path)

    print(f'Všechny procesy pro obec {city_name} byly úspěšně provedeny')

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print('Příklad využití -> python manual_run.py "Název obce" user@gmail.com')
    else:
        run_pipeline(sys.argv[1], sys.argv[2])
