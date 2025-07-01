import os
import pdfplumber
import tiktoken
import gspread
from datetime import datetime
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from fallback_via_ia import fallback_via_ia_batch

# === CONFIGURAÇÕES ===
PASTA_PDFS = r"C:" # <-- ALTERE PARA O CAMINHO DA SUA PASTA
EXTENSOES_VALIDAS = [".pdf"]
ARQUIVO_CREDENCIAIS = "credentials.json"
NOME_PLANILHA = "OCR CCB"
NOME_ABA = "Novo teste"
LIMITE_TOKENS = 90000
SALVAR_DEBUG = False

# === FUNÇÕES UTILITÁRIAS ===

def conectar_planilha():
    escopo = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(ARQUIVO_CREDENCIAIS, escopo)
    cliente = gspread.authorize(creds)
    return cliente.open(NOME_PLANILHA).worksheet(NOME_ABA)

def contar_tokens(texto, modelo="gpt-3.5-turbo"):
    try:
        enc = tiktoken.encoding_for_model(modelo)
    except:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(texto))

def extrair_paginas_relevantes(path_pdf):
    try:
        with pdfplumber.open(path_pdf) as pdf:
            total = len(pdf.pages)
            indices = [0, 1] if total >= 2 else [0]
            if total > 2:
                indices.append(total - 1)

            texto = ""
            for i in indices:
                texto_pagina = pdf.pages[i].extract_text()
                if texto_pagina:
                    texto += texto_pagina + "\n"

            return texto
    except Exception as e:
        print(f"❌ Erro ao abrir {path_pdf}: {e}")
        return ""

def limpar_texto(texto):
    linhas = texto.splitlines()
    linhas = [linha.strip() for linha in linhas if linha.strip()]
    return "\n".join(linhas)

def salvar_debug(texto, nome):
    with open(f"debug_{nome}.txt", "w", encoding="utf-8") as f:
        f.write(texto)

def carregar_arquivos_existentes(sheet):
    valores = sheet.col_values(15)
    return set(valores[1:])

def montar_linha_planilha(dado):
    return [
        dado.get("numero_proposta", ""),
        dado.get("nome_cliente", ""),
        dado.get("cpf_cliente", ""),
        dado.get("valor_total", ""),
        dado.get("valor_liberado", ""),
        dado.get("valor_outras_liquidacoes", ""),
        dado.get("tarifa_cadastro", ""),
        dado.get("seguro", ""),
        dado.get("valor_iof", ""),
        dado.get("taxa_juros_mensal", ""),
        dado.get("taxa_juros_anual", ""),
        dado.get("primeiro_vencimento", ""),
        dado.get("quantidade_parcelas", ""),
        dado.get("valor_parcela", ""),
        dado.get("cet", ""),
        dado.get("data_assinatura", ""),
        dado.get("arquivo", ""),
        dado.get("tipo_comprovante", "CCB"),
        dado.get("metodo_extracao", "fallback_ia")
    ]

def eh_modelo_nao_ccb(texto):
    # Verifica se é o modelo conhecido que começa com "DADOS PESSOAIS"
    return texto.strip().upper().startswith("DADOS PESSOAIS")

def processar_pasta(pasta):
    sheet = conectar_planilha()
    arquivos_existentes = carregar_arquivos_existentes(sheet)

    arquivos = [
        os.path.join(pasta, nome)
        for nome in os.listdir(pasta)
        if nome.lower().endswith(".pdf")
    ]

    lote_atual = []
    tokens_total = 0
    resultados_finais = []

    for caminho in arquivos:
        nome = os.path.basename(caminho)
        if nome in arquivos_existentes:
            print(f"⏭️ {nome} já está na planilha. Ignorando.")
            continue

        print(f"\n📄 Processando: {nome}")
        texto_bruto = extrair_paginas_relevantes(caminho)
        texto_limpo = limpar_texto(texto_bruto)
        if eh_modelo_nao_ccb(texto_limpo):
            print(f"⚠️ Documento '{nome}' identificado como NÃO CCB. Registrando apenas nome do arquivo.")
            resultados_finais.append({
                "numero_proposta": "",
                "nome_cliente": "",
                "cpf_cliente": "",
                "valor_total": "",
                "valor_liberado": "",
                "valor_outras_liquidacoes": "",
                "tarifa_cadastro": "",
                "seguro": "",
                "valor_iof": "",
                "taxa_juros_mensal": "",
                "taxa_juros_anual": "",
                "primeiro_vencimento": "",
                "quantidade_parcelas": "",
                "valor_parcela": "",
                "cet": "",
                "data_assinatura": "",
                "arquivo": nome,
                "tipo_comprovante": "NÃO É UMA CCB",
                "metodo_extracao": "modelo_nao_ccb"
            })
            continue
        tokens = contar_tokens(texto_limpo)

        print(f"🧠 Tokens estimados: {tokens}")
        if SALVAR_DEBUG:
            salvar_debug(texto_limpo, nome.replace(".pdf", ""))

        lote_atual.append({
            "arquivo": nome,
            "texto": texto_limpo
        })
        tokens_total += tokens

        if tokens_total >= LIMITE_TOKENS:
            print(f"🚀 Enviando lote para IA...")
            respostas = fallback_via_ia_batch(lote_atual)
            resultados_finais.extend(respostas)
            lote_atual, tokens_total = [], 0

    # Enviar o último lote
    if lote_atual:
        print(f"🚀 Enviando lote final para IA...")
        respostas = fallback_via_ia_batch(lote_atual)
        resultados_finais.extend(respostas)

    # Adicionar à planilha os que não são duplicados
    novas_linhas = []
    for r in resultados_finais:
        if r.get("arquivo") not in arquivos_existentes:
            novas_linhas.append(montar_linha_planilha(r))

    if novas_linhas:
        print(f"📥 Enviando {len(novas_linhas)} novas CCBs para a planilha...")
        sheet.append_rows(novas_linhas, value_input_option='USER_ENTERED')
    else:
        print("📭 Nenhuma nova linha para adicionar.")

if __name__ == "__main__":
    processar_pasta(PASTA_PDFS)
