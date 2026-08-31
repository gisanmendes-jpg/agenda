import streamlit as st
import pandas as pd
from sqlalchemy import text

st.set_page_config(page_title="Agenda Compartilhada", layout="centered")

# 1. Conexão com o banco de dados na nuvem (busca a URL nos Secrets)
conn = st.connection("postgresql", type="sql")

# Criar a tabela na primeira vez que o app rodar
def criar_tabela():
    with conn.session as s:
        s.execute(text('''CREATE TABLE IF NOT EXISTS eventos 
                         (data TEXT, hora TEXT, titulo TEXT, responsavel TEXT)'''))
        s.commit()

criar_tabela()

st.title("📅 Agenda Compartilhada")

# 2. Formulário para adicionar eventos
with st.form("novo_evento"):
    st.subheader("Agendar Novo Evento")
    col1, col2 = st.columns(2)
    
    data = col1.date_input("Data")
    hora = col2.time_input("Hora")
    titulo = st.text_input("Título do Evento")
    responsavel = st.text_input("Seu Nome / Responsável")
    
    submit = st.form_submit_button("Salvar Evento")
    
    if submit and titulo:
        # Inserção segura dos dados no banco
        with conn.session as s:
            s.execute(
                text('INSERT INTO eventos (data, hora, titulo, responsavel) VALUES (:data, :hora, :titulo, :responsavel)'),
                {"data": data.strftime("%Y-%m-%d"), "hora": hora.strftime("%H:%M"), "titulo": titulo, "responsavel": responsavel}
            )
            s.commit()
        st.success("Evento agendado com sucesso!")
        st.rerun()

# 3. Exibir os eventos agendados
st.divider()
st.subheader("Próximos Eventos")

# Busca os dados (ttl=0 garante que a tabela não fique salva em cache e mostre dados velhos)
df = conn.query("SELECT * FROM eventos ORDER BY data, hora", ttl="0m")

if not df.empty:
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum evento agendado ainda. Use o formulário acima para começar.")
