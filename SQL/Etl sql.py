import pandas as pd
import sqlite3
import os

ARQUIVO_HISTORICO = "FTD_Historico.xlsx"
BANCO = "ftd_analytics.db"
SCHEMA = "schema.sql"

# 1. Recria o banco do zero a cada rodada (fonte da verdade é sempre o histórico Excel)
if os.path.exists(BANCO):
    os.remove(BANCO)

conn = sqlite3.connect(BANCO)
cur = conn.cursor()
with open(SCHEMA, encoding="utf-8") as f:
    cur.executescript(f.read())

# 2. Lê a base histórica acumulada
base = pd.read_excel(ARQUIVO_HISTORICO, sheet_name="Historico")

MAPA_TIPOS = {
    "CNPJ": "CNPJ",
    "DATA DE EMISS": "Data",
    "NUMERO DO DOC": "Numero",
    "VALOR DIVERGENTE": "Valor",
    "DOC DIVERGENTE": "DOC",
}

def classificar(erro):
    if pd.isna(erro):
        return []
    tipos = [tipo for chave, tipo in MAPA_TIPOS.items() if chave in erro]
    return tipos if tipos else ["Outro"]

# 3. Popula Dim_Obra
for obra in sorted(base["Obra"].dropna().unique()):
    cur.execute("INSERT OR IGNORE INTO Dim_Obra (obra_nome) VALUES (?)", (obra,))

# 4. Popula Dim_Credor
for credor in sorted(base["Credor"].dropna().unique()):
    cur.execute("INSERT OR IGNORE INTO Dim_Credor (credor_nome) VALUES (?)", (credor,))

# 5. Popula Dim_Mes
for competencia in sorted(base["Mes"].dropna().unique()):
    ano, mes = competencia.split("-")
    cur.execute(
        "INSERT OR IGNORE INTO Dim_Mes (competencia, ano, mes) VALUES (?, ?, ?)",
        (competencia, int(ano), int(mes)),
    )

# 6. Popula Dim_Tipo_Erro
todos_tipos = sorted({t for erro in base["Erro"] for t in classificar(erro)})
for tipo in todos_tipos:
    cur.execute("INSERT OR IGNORE INTO Dim_Tipo_Erro (tipo_erro) VALUES (?)", (tipo,))

conn.commit()

# 7. Mapas nome -> id para popular a fato rapidamente
obra_map = dict(cur.execute("SELECT obra_nome, obra_id FROM Dim_Obra").fetchall())
credor_map = dict(cur.execute("SELECT credor_nome, credor_id FROM Dim_Credor").fetchall())
mes_map = dict(cur.execute("SELECT competencia, mes_id FROM Dim_Mes").fetchall())
tipo_map = dict(cur.execute("SELECT tipo_erro, tipo_erro_id FROM Dim_Tipo_Erro").fetchall())

# 8. Popula Fato_Lancamentos + tabela-ponte de erros
for _, row in base.iterrows():
    status = "sem erro" if pd.isna(row["Erro"]) else "com erro"
    cur.execute(
        """INSERT INTO Fato_Lancamentos (lancamento_num, obra_id, credor_id, mes_id, valor, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            int(row["Lancamento"]),
            obra_map[row["Obra"]],
            credor_map[row["Credor"]],
            mes_map[row["Mes"]],
            float(row["Valor"]) if pd.notna(row["Valor"]) else None,
            status,
        ),
    )
    fato_id = cur.lastrowid
    for tipo in classificar(row["Erro"]):
        cur.execute(
            "INSERT INTO Fato_Lancamento_Erro (fato_id, tipo_erro_id) VALUES (?, ?)",
            (fato_id, tipo_map[tipo]),
        )

conn.commit()
print(f"Banco '{BANCO}' populado: {len(base)} lançamentos carregados.\n")

# ============================================
# Consultas de análise (exemplos para o portfólio)
# ============================================

print("=== 1. Lançamentos e taxa de erro por obra ===")
q1 = """
SELECT
    o.obra_nome,
    COUNT(*) AS total_lancamentos,
    SUM(CASE WHEN f.status = 'com erro' THEN 1 ELSE 0 END) AS com_erro,
    ROUND(100.0 * SUM(CASE WHEN f.status = 'com erro' THEN 1 ELSE 0 END) / COUNT(*), 2) AS taxa_erro_pct
FROM Fato_Lancamentos f
JOIN Dim_Obra o ON o.obra_id = f.obra_id
GROUP BY o.obra_nome
ORDER BY com_erro DESC;
"""
print(pd.read_sql(q1, conn).to_string(index=False))

print("\n=== 2. Evolução mensal ===")
q2 = """
SELECT
    m.competencia,
    COUNT(*) AS total_lancamentos,
    SUM(CASE WHEN f.status = 'com erro' THEN 1 ELSE 0 END) AS com_erro,
    ROUND(100.0 * SUM(CASE WHEN f.status = 'com erro' THEN 1 ELSE 0 END) / COUNT(*), 2) AS taxa_erro_pct
FROM Fato_Lancamentos f
JOIN Dim_Mes m ON m.mes_id = f.mes_id
GROUP BY m.competencia
ORDER BY m.competencia;
"""
print(pd.read_sql(q2, conn).to_string(index=False))

print("\n=== 3. Erros por tipo ===")
q3 = """
SELECT
    te.tipo_erro,
    COUNT(*) AS quantidade
FROM Fato_Lancamento_Erro fe
JOIN Dim_Tipo_Erro te ON te.tipo_erro_id = fe.tipo_erro_id
GROUP BY te.tipo_erro
ORDER BY quantidade DESC;
"""
print(pd.read_sql(q3, conn).to_string(index=False))

print("\n=== 4. Top 10 credores com mais valor divergente ===")
q4 = """
SELECT
    c.credor_nome,
    COUNT(*) AS lancamentos_com_erro,
    ROUND(SUM(f.valor), 2) AS valor_total_divergente
FROM Fato_Lancamentos f
JOIN Dim_Credor c ON c.credor_id = f.credor_id
WHERE f.status = 'com erro'
GROUP BY c.credor_nome
ORDER BY valor_total_divergente DESC
LIMIT 10;
"""
print(pd.read_sql(q4, conn).to_string(index=False))

# ============================================
# Exporta as tabelas do modelo para Excel — pronto pra importar no Power BI
# sem precisar de driver ODBC (útil em máquina corporativa sem permissão
# de administrador para instalar drivers de terceiros).
# ============================================
with pd.ExcelWriter("FTD_Modelo_PowerBI.xlsx", engine="openpyxl") as writer:
    pd.read_sql("SELECT * FROM Dim_Obra", conn).to_excel(writer, sheet_name="Dim_Obra", index=False)
    pd.read_sql("SELECT * FROM Dim_Credor", conn).to_excel(writer, sheet_name="Dim_Credor", index=False)
    pd.read_sql("SELECT * FROM Dim_Mes", conn).to_excel(writer, sheet_name="Dim_Mes", index=False)
    pd.read_sql("SELECT * FROM Dim_Tipo_Erro", conn).to_excel(writer, sheet_name="Dim_Tipo_Erro", index=False)
    pd.read_sql("SELECT * FROM Fato_Lancamentos", conn).to_excel(writer, sheet_name="Fato_Lancamentos", index=False)
    pd.read_sql("SELECT * FROM Fato_Lancamento_Erro", conn).to_excel(writer, sheet_name="Fato_Lancamento_Erro", index=False)

print("\n'FTD_Modelo_PowerBI.xlsx' gerado — importe cada aba no Power BI (Get Data > Excel).")

conn.close()
