import streamlit as st
import pandas as pd
from sqlalchemy import text

st.set_page_config(page_title="Agenda Compartilhada", layout="centered")

# 1. Defina quem pode acessar a agenda
EMAILS_AUTORIZADOS = ["gisanmendes@gmail.com", "outrapessoa@gmail.com"]

# 2. Inicializa o controle de acesso na sessão
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

# 3. Tela de Login
if not st.session_state.autenticado:
    st.title("🔒 Acesso Restrito")
    st.write("Por favor, identifique-se para acessar a agenda.")
    
    email_digitado = st.text_input("Seu e-mail")
    
    if st.button("Entrar"):
        if email_digitado.strip().lower() in EMAILS_AUTORIZADOS:
            st.session_state.autenticado = True
            st.rerun() # Recarrega a página para mostrar a agenda
        else:
            st.error("E-mail não autorizado. Verifique a digitação.")

# 4. O Aplicativo Principal (Só aparece se autenticado)
else:
    # Botão para deslogar no topo da página
    col_vazia, col_sair = st.columns([4, 1])
    with col_sair:
        if st.button("Sair"):
            st.session_state.autenticado = False
            st.rerun()

    # Conexão com o Supabase
    conn = st.connection("postgresql", type="sql")

    def criar_tabela():
        with conn.session as s:
            s.execute(text('''CREATE TABLE IF NOT EXISTS eventos 
                             (data TEXT, hora TEXT, titulo TEXT, responsavel TEXT)'''))
            s.commit()

    criar_tabela()

    st.title("📅 Agenda Compartilhada")

    with st.form("novo_evento"):
        st.subheader("Agendar Novo Evento")
        col1, col2 = st.columns(2)
        
        data = col1.date_input("Data")
        hora = col2.time_input("Hora")
        titulo = st.text_input("Título do Evento")
        responsavel = st.text_input("Seu Nome / Responsável")
        
        submit = st.form_submit_button("Salvar Evento")
        
        if submit and titulo:
            with conn.session as s:
                s.execute(
                    text('INSERT INTO eventos (data, hora, titulo, responsavel) VALUES (:data, :hora, :titulo, :responsavel)'),
                    {"data": data.strftime("%Y-%m-%d"), "hora": hora.strftime("%H:%M"), "titulo": titulo, "responsavel": responsavel}
                )
                s.commit()
            st.success("Evento agendado com sucesso!")
            st.rerun()

    st.divider()
    st.subheader("Próximos Eventos")

    try:
        df = conn.query("SELECT * FROM eventos ORDER BY data, hora", ttl="0m")
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum evento agendado ainda. Use o formulário acima para começar.")
    except Exception as e:
        st.error(f"Erro ao carregar os eventos: {e}")
