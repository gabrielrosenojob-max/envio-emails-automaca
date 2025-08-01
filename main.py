# ENVIO AUTOMÁTICO + COLETA DE EMAILS PARA SERVIDOR (REPLIT)

import os
import smtplib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import time
from threading import Thread
from flask import Flask

# === CONFIGURAÇÕES ===
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
LIMITE_DIARIO = 300
ARQUIVO_ENVIADOS = "emails_enviados.txt"
CURRICULO_PATH = "Curriculum.pdf"

# === LER VARIAÇÕES DE ASSUNTO E CORPO ===
def carregar_variacoes(arquivo):
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            blocos = f.read().split("---") if "corpo" in arquivo else f.readlines()
            return [b.strip() for b in blocos if b.strip()]
    return []

ASSUNTOS = carregar_variacoes("assuntos_email.txt")
CORPOS = carregar_variacoes("corpos_email.txt")

# === COLETAR EMAILS ===
def coletar_emails_seasonal():
    emails = set()
    try:
        r = requests.post(
            "https://api.seasonaljobs.dol.gov/datahub/search?api-version=2020-06-30",
            json={"search": "", "filter": "active eq true", "top": 1000, "select": "*"},
            headers={"User-Agent": "Mozilla/5.0"}
        )
        for v in r.json().get("value", []):
            begin_date = v.get("begin_date")
            if begin_date:
                begin_date = begin_date.replace("Z", "")
                if datetime.strptime(begin_date, "%Y-%m-%dT%H:%M:%S") >= datetime(2024, 7, 1):
                    url = f"https://seasonaljobs.dol.gov/jobs/{v['case_number']}"
                    res = requests.get(url)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    email_el = soup.find('a', href=lambda h: h and 'mailto:' in h)
                    if email_el:
                        emails.add(email_el.get_text().lower())
    except Exception as e:
        print("Erro ao coletar emails do seasonaljobs:", e)
    return emails

def coletar_emails_el_portal():
    base_url = "https://elportalmigrante.org/en/jobs?rubro=Agricultural%20%20Workers&estado=All&sort_by=created"
    emails = set()
    try:
        response = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        job_links = ["https://elportalmigrante.org" + l['href'] for l in links if "/en/jobs/" in l['href']]
        for link in job_links:
            try:
                job_page = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
                job_soup = BeautifulSoup(job_page.text, 'html.parser')
                email_tag = job_soup.find('a', href=lambda h: h and 'mailto:' in h)
                if email_tag:
                    emails.add(email_tag.get_text().strip().lower())
                time.sleep(0.25)
            except:
                continue
    except Exception as e:
        print("Erro ao coletar emails do El Portal:", e)
    return emails

# === LER EMAILS JÁ ENVIADOS ===
def carregar_enviados():
    if not os.path.exists(ARQUIVO_ENVIADOS):
        return set()
    with open(ARQUIVO_ENVIADOS, 'r') as f:
        return set(l.strip() for l in f.readlines())

# === ENVIAR EMAIL ===
def enviar_email(destinatario):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = destinatario
        msg['Subject'] = random.choice(ASSUNTOS) if ASSUNTOS else "H-2A Job Application"
        corpo = random.choice(CORPOS) if CORPOS else "Hello, my name is Gabriel Roseno. I am applying for the H-2A job opportunity."
        msg.attach(MIMEText(corpo, 'plain'))
        with open(CURRICULO_PATH, 'rb') as f:
            attach = MIMEText(f.read(), 'base64', 'utf-8')
            attach.add_header('Content-Disposition', 'attachment', filename="Curriculum.pdf")
            msg.attach(attach)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_ADDRESS, destinatario, msg.as_string())
        print(f"Email enviado para: {destinatario}")
        return True
    except Exception as e:
        print(f"Erro ao enviar para {destinatario}: {e}")
        return False

# === EXECUÇÃO PRINCIPAL ===
def executar():
    enviados = carregar_enviados()
    novos_emails = coletar_emails_seasonal().union(coletar_emails_el_portal())
    nao_enviados = list(novos_emails - enviados)
    enviados_hoje = 0
    for email in nao_enviados:
        if enviados_hoje >= LIMITE_DIARIO:
            print("Limite de envios diários atingido.")
            break
        if enviar_email(email):
            with open(ARQUIVO_ENVIADOS, 'a') as f:
                f.write(email + '\n')
            enviados_hoje += 1
        time.sleep(random.uniform(30, 90))

# === SERVIDOR FLASK PARA MANTER ONLINE ===
app = Flask('')

@app.route('/')
def home():
    return "Rodando automaticamente."

def manter_online():
    app.run(host='0.0.0.0', port=8080)

@app.route('/rodar')
def rodar_envio():
    Thread(target=executar).start()
    return "Envio iniciado."

def manter_online():
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    Thread(target=manter_online).start()
    Thread(target=executar).start()



# Use o agendador do Replit ou UptimeRobot para rodar isso 1x por dia
