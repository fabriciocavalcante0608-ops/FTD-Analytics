import pandas as pd
import os

# ======= CONFIGURAÇÃO DO MÊS =======
# Ajuste isso a cada novo mês antes de rodar
ARQUIVO_NOVO = "FTD 08 - Copia (2).xlsx"
COMPETENCIA = "2026-08"          # AAAA-MM do arquivo que está sendo importado agora
ARQUIVO_HISTORICO = "FTD_Historico.xlsx"   # base acumulada (não apagar/mover)

# 1. Lê o arquivo novo (exportação do mês)
novo = pd.read_excel(ARQUIVO_NOVO, sheet_name="Base")
novo.columns = ["Obra", "Credor", "Valor", "Lancamento", "Erro"] + list(novo.columns[5:])
novo = novo[["Obra", "Credor", "Valor", "Lancamento", "Erro"]]
novo["Mes"] = COMPETENCIA

# 2. Junta com o histórico já acumulado (se existir)
if os.path.exists(ARQUIVO_HISTORICO):
    historico = pd.read_excel(ARQUIVO_HISTORICO, sheet_name="Historico")
    base = pd.concat([historico, novo], ignore_index=True)
else:
    base = novo.copy()

# 3. Remove duplicados: só remove se Obra+Credor+Valor+Lancamento+Erro forem
# TODOS iguais (reimportação acidental da mesma linha). Lançamento sozinho
# não é chave única: a mesma obra pode ter parcelas diferentes com o mesmo
# número de lançamento e valores distintos — essas continuam sendo mantidas.
antes = len(base)
base = base.drop_duplicates(subset=["Obra", "Credor", "Valor", "Lancamento", "Erro"], keep="last")
duplicados_removidos = antes - len(base)

# 4. Status e Tipo_erro (recalculado sobre o acumulado inteiro)
base["Status"] = base["Erro"].apply(lambda x: "sem erro" if pd.isna(x) else "com erro")

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

base["Tipo_erro"] = base["Erro"].apply(classificar)

# 5. Indicadores gerais (acumulado)
total = len(base)
com_erro = (base["Status"] == "com erro").sum()
sem_erro = total - com_erro
taxa_erro = com_erro / total

print(f"=== IMPORTAÇÃO {COMPETENCIA} ===")
print(f"Linhas novas no arquivo: {len(novo)}")
print(f"Duplicados removidos (já existiam): {duplicados_removidos}")
print()
print("=== INDICADORES GERAIS (ACUMULADO TOTAL) ===")
print(f"Total de lançamentos: {total}")
print(f"Com erro: {com_erro}")
print(f"Sem erro: {sem_erro}")
print(f"Taxa de erro: {taxa_erro:.2%}")

# 6. Erros por tipo
tipos_explodidos = base["Tipo_erro"].explode().dropna()
print("\n=== ERROS POR TIPO (ACUMULADO) ===")
print(tipos_explodidos.value_counts())

# 7. Erros por obra
resumo_obra = (
    base.groupby("Obra")
    .agg(Total=("Status", "count"), Erros=("Status", lambda s: (s == "com erro").sum()))
    .reset_index()
)
resumo_obra["Acuracia"] = (resumo_obra["Total"] - resumo_obra["Erros"]) / resumo_obra["Total"]
resumo_obra["Erro_%"] = 1 - resumo_obra["Acuracia"]
resumo_obra = resumo_obra.sort_values("Erros", ascending=False)

print("\n=== ERROS POR OBRA (ACUMULADO) ===")
print(resumo_obra.to_string(index=False))

# 8. NOVO: evolução mensal (o motivo de termos a coluna Mês)
resumo_mes = (
    base.groupby("Mes")
    .agg(Total=("Status", "count"), Erros=("Status", lambda s: (s == "com erro").sum()))
    .reset_index()
)
resumo_mes["Taxa_erro"] = resumo_mes["Erros"] / resumo_mes["Total"]

print("\n=== EVOLUÇÃO MENSAL ===")
print(resumo_mes.to_string(index=False))

# 9. Salva o histórico atualizado (para o próximo mês) e o resultado consolidado
base.to_excel(ARQUIVO_HISTORICO, sheet_name="Historico", index=False)

with pd.ExcelWriter("FTD_Analytics_Resultado.xlsx", engine="openpyxl") as writer:
    base.explode("Tipo_erro").to_excel(writer, sheet_name="Base_Tratada", index=False)
    resumo_obra.to_excel(writer, sheet_name="Erros_por_Obra", index=False)
    tipos_explodidos.value_counts().rename_axis("Tipo_erro").reset_index(name="Qtd").to_excel(
        writer, sheet_name="Erros_por_Tipo", index=False
    )
    resumo_mes.to_excel(writer, sheet_name="Evolucao_Mensal", index=False)

print(f"\n'{ARQUIVO_HISTORICO}' atualizado e 'FTD_Analytics_Resultado.xlsx' gerado com sucesso.")