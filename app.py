import streamlit as st
import pandas as pd
from sqlalchemy import text
from streamlit_calendar import calendar

st.set_page_config(page_title="Agenda Compartilhada", layout="wide")

EMAILS_AUTORIZADOS = ["gisanmendes@gmail.com", "fabioadriano044@@gmail.com"]

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito")
    email_digitado = st.text_input("Seu e-mail")
    
    if st.button("Entrar"):
        if email_digitado.strip().lower() in EMAILS_AUTORIZADOS:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("E-mail não autorizado.")
# ... (O cabeçalho e a tela de Login permanecem exatamente iguais) ...

else:
    col_vazia, col_sair = st.columns([4, 1])
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

    # 1. Formulário (Fica de fora da atualização automática para não apagar durante a digitação)
    with st.form("novo_evento"):
        col1, col2, col3, col4 = st.columns(4)
        data = col1.date_input("Data")
        hora = col2.time_input("Hora")
        titulo = col3.text_input("Título")
        responsavel = col4.text_input("Responsável")
        
        if st.form_submit_button("Agendar Horário") and titulo:
            with conn.session as s:
                s.execute(
                    text('INSERT INTO eventos (data, hora, titulo, responsavel) VALUES (:data, :hora, :titulo, :responsavel)'),
                    {"data": data.strftime("%Y-%m-%d"), "hora": hora.strftime("%H:%M"), "titulo": titulo, "responsavel": responsavel}
                )
                s.commit()
            st.success("Agendado!")
            st.rerun()

  

    # 2. Fragmento de Tempo Real (Roda de forma independente a cada 10 segundos)
    @st.fragment(run_every="10s")
    def painel_em_tempo_real():
        try:
            # Busca os dados mais recentes no Supabase
            df = conn.query("SELECT * FROM eventos ORDER BY data, hora", ttl="0m")
            
            with st.expander("Gerenciar / Excluir Eventos"):
                if not df.empty:
                    selecao = st.dataframe(df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
                    linhas = selecao.selection.rows
                    if len(linhas) > 0:
                        evento = df.iloc[linhas[0]]
                        if st.button(f"🗑️ Excluir '{evento['titulo']}'", type="primary"):
                            with conn.session as s:
                                s.execute(
                                    text("DELETE FROM eventos WHERE data=:data AND hora=:hora AND titulo=:titulo"),
                                    {"data": evento['data'], "hora": evento['hora'], "titulo": evento['titulo']}
                                )
                                s.commit()
                            st.rerun() # Atualiza apenas este fragmento
                else:
                    st.info("Nenhum evento agendado.")

            st.subheader("Visão Geral de Disponibilidade")
            
            eventos_visuais = []
            if not df.empty:
                for _, row in df.iterrows():
                    inicio = f"{row['data']}T{row['hora']}:00"
                    eventos_visuais.append({
                        "title": f"Ocupado: {row['titulo']}",
                        "start": inicio,
                        "color": "#17803d"
                    })
            
            opcoes_calendario = {
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

    # 3. Executa a função do fragmento na tela
    painel_em_tempo_real()
