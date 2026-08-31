import streamlit as st
import pandas as pd
from sqlalchemy import text
from streamlit_calendar import calendar

st.set_page_config(page_title="Agenda Compartilhada", layout="wide")

# 1. Defina os nomes simples autorizados
NOMES_AUTORIZADOS = ["Gisa", "Fabio", "Andre"]

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito")
    nome_digitado = st.text_input("Digite seu Nome")
    
    if st.button("Entrar"):
        # Converte para letras minúsculas para ignorar diferenças (ex: 'Gisele' e 'gisele' vão funcionar)
        nomes_validos = [n.strip().lower() for n in NOMES_AUTORIZADOS]
        
        if nome_digitado.strip().lower() in nomes_validos:
            st.session_state.autenticado = True
            # Salva o nome formatado na sessão para usar no preenchimento automático depois
            st.session_state.usuario_atual = nome_digitado.strip().title()
            st.rerun()
        else:
            st.error("Nome não reconhecido. Verifique a digitação.")
else:
    # Mostra quem está logado no topo da tela, ao lado do botão de sair
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

    with st.form("novo_evento"):
        col1, col2, col3, col4 = st.columns(4)
        data = col1.date_input("Data")
        hora = col2.time_input("Hora")
        titulo = col3.text_input("Título")
        
        # O campo Responsável já vem preenchido com o nome de quem fez login
        responsavel = col4.text_input("Responsável", value=st.session_state.usuario_atual)
        
        if st.form_submit_button("Agendar Horário") and titulo:
            with conn.session as s:
                s.execute(
                    text('INSERT INTO eventos (data, hora, titulo, responsavel) VALUES (:data, :hora, :titulo, :responsavel)'),
                    {"data": data.strftime("%Y-%m-%d"), "hora": hora.strftime("%H:%M"), "titulo": titulo, "responsavel": responsavel}
                )
                s.commit()
            st.success("Agendado!")
            st.rerun()

    st.divider()

    @st.fragment(run_every="10s")
    def painel_em_tempo_real():
        try:
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
                            st.rerun()
                else:
                    st.info("Nenhum evento agendado.")

            st.subheader("Visão Geral de Disponibilidade")
            
            eventos_visuais = []
            if not df.empty:
                for _, row in df.iterrows():
                    inicio = f"{row['data']}T{row['hora']}:00"
                    eventos_visuais.append({
                        # O calendário agora mostra o título do evento e quem marcou
                        "title": f"{row['titulo']} ({row['responsavel']})",
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

    painel_em_tempo_real()
