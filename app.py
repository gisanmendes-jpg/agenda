import streamlit as st
import pandas as pd
from sqlalchemy import text
from streamlit_calendar import calendar
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

st.set_page_config(page_title="Agenda Compartilhada", layout="wide")

# 1. Dicionário vinculando os nomes aos e-mails que receberão os avisos
USUARIOS = {
    "gisa": "gisanmendes@gmail.com",
    "fabio": "fabioadriano044@gmail.com",
    "andre": "gisanmendes@gmail.com"
}

# Função disparadora de e-mails
def enviar_aviso(destinatario, assunto, corpo):
    try:
        remetente = st.secrets["email"]["endereco"]
        senha = st.secrets["email"]["senha"]
        
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        st.toast(f"Aviso: Houve falha ao enviar o e-mail para {destinatario} ({e})")

# Inicialização da sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "usuario_atual" not in st.session_state:
    st.session_state.usuario_atual = ""

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito")
    nome_digitado = st.text_input("Digite seu Nome")
    
    if st.button("Entrar"):
        if nome_digitado.strip().lower() in USUARIOS:
            st.session_state.autenticado = True
            st.session_state.usuario_atual = nome_digitado.strip().title()
            st.rerun()
        else:
            st.error("Nome não reconhecido. Verifique a digitação.")
else:
    col_vazia, col_info, col_sair = st.columns([3, 1, 1])
    with col_info:
        st.write(f"👤 Olá, {st.session_state.usuario_atual}")
    with col_sair:
        if st.button("Sair"):
            st.session_state.autenticado = False
            st.rerun()

    conn = st.connection("postgresql", type="sql")

    def criar_tabela():
        with conn.session as s:
            s.execute(text('''CREATE TABLE IF NOT EXISTS eventos 
                             (data TEXT, hora TEXT, titulo TEXT, responsavel TEXT)'''))
            s.commit()
    criar_tabela()

    st.title("📅 Agenda Compartilhada")

    with st.form("novo_evento", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        data = col1.date_input("Data", format="DD/MM/YYYY")
        hora = col2.time_input("Hora")
        titulo = col3.text_input("Título")
        responsavel = col4.text_input("Responsável", value=st.session_state.usuario_atual)
        
        if st.form_submit_button("Agendar Horário"):
            if not titulo.strip():
                st.warning("⚠️ O campo 'Título' é obrigatório para salvar o evento.")
            else:
                with conn.session as s:
                    s.execute(
                        text('INSERT INTO eventos (data, hora, titulo, responsavel) VALUES (:data, :hora, :titulo, :responsavel)'),
                        {"data": data.strftime("%Y-%m-%d"), "hora": hora.strftime("%H:%M"), "titulo": titulo, "responsavel": responsavel}
                    )
                    s.commit()
                
                # NOVO: Dispara e-mail para TODOS da lista
                assunto = f"📅 Novo Agendamento: {titulo}"
                for nome, email_destinatario in USUARIOS.items():
                    corpo = f"Olá {nome.title()},\n\nUm novo compromisso foi adicionado à agenda por {st.session_state.usuario_atual}.\n\n📌 Título: {titulo}\n👤 Responsável: {responsavel}\n📅 Data: {data.strftime('%d/%m/%Y')}\n⏰ Hora: {hora.strftime('%H:%M')}\n\nAcesse o aplicativo para ver a disponibilidade geral."
                    enviar_aviso(email_destinatario, assunto, corpo)
                    
                st.success("✅ Agendado! Todos os usuários foram notificados.")
                time.sleep(1.5)
                st.rerun()

    st.divider()

    @st.fragment(run_every="10s")
    def painel_em_tempo_real():
        try:
            df = conn.query("SELECT * FROM eventos ORDER BY data, hora", ttl="0m")
            
            if not df.empty:
                df['data'] = pd.to_datetime(df['data']).dt.date
            
            with st.expander("Gerenciar / Excluir Eventos"):
                if not df.empty:
                    selecao = st.dataframe(
                        df, 
                        use_container_width=True, 
                        hide_index=True, 
                        on_select="rerun", 
                        selection_mode="single-row",
                        column_config={
                            "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY")
                        }
                    )
                    linhas = selecao.selection.rows
                    if len(linhas) > 0:
                        evento = df.iloc[linhas[0]]
                        if st.button(f"🗑️ Excluir '{evento['titulo']}'", type="primary"):
                            with conn.session as s:
                                s.execute(
                                    text("DELETE FROM eventos WHERE data=:data AND hora=:hora AND titulo=:titulo"),
                                    {"data": evento['data'].strftime("%Y-%m-%d"), "hora": evento['hora'], "titulo": evento['titulo']}
                                )
                                s.commit()
                            
                            # NOVO: Dispara e-mail de exclusão para TODOS da lista
                            assunto = f"❌ Cancelamento: {evento['titulo']}"
                            for nome, email_destinatario in USUARIOS.items():
                                corpo = f"Olá {nome.title()},\n\nO compromisso abaixo foi cancelado da agenda por {st.session_state.usuario_atual}.\n\n📌 Título: {evento['titulo']}\n👤 Responsável: {evento['responsavel']}\n📅 Data: {evento['data'].strftime('%d/%m/%Y')}\n⏰ Hora: {evento['hora']}"
                                enviar_aviso(email_destinatario, assunto, corpo)
                            
                            st.success("✅ Evento cancelado. Todos os usuários foram notificados!")
                            time.sleep(1.5)
                            st.rerun()
                else:
                    st.info("Nenhum evento agendado.")

            st.subheader("Visão Geral de Disponibilidade")
            
            eventos_visuais = []
            if not df.empty:
                for _, row in df.iterrows():
                    inicio = f"{row['data'].strftime('%Y-%m-%d')}T{row['hora']}:00"
                    eventos_visuais.append({
                        "title": f"{row['titulo']} ({row['responsavel']})",
                        "start": inicio,
                        "color": "#17803d"
                    })
            
            opcoes_calendario = {
                "locale": "pt-br",
                "buttonText": {
                    "today": "Hoje",
                    "week": "Semana",
                    "day": "Dia"
                },
                "headerToolbar": {
                    "left": "today prev,next",
                    "center": "title",
                    "right": "timeGridWeek,timeGridDay"
                },
                "initialView": "timeGridWeek",
                "slotMinTime": "06:00:00",
                "slotMaxTime": "22:00:00",
                "allDaySlot": False,
            }
            
            calendar(events=eventos_visuais, options=opcoes_calendario)
                
        except Exception as e:
            st.error(f"Erro: {e}")

    painel_em_tempo_real()
