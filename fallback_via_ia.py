import os
import time
import openai
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gerar_prompt(texto, nome_arquivo):
    return f"""
Você é um assistente de extração de dados de contratos CCB. Extraia as seguintes informações em formato JSON:

- "numero_proposta": número da proposta ou do contrato — geralmente aparece como "Proposta nº", "Nº do Instrumento", "Número do Contrato", "Número da CCB", ou similar
- "nome_cliente": nome completo da pessoa contratante
- "valor_total": valor total do contrato
- "valor_liberado": valor líquido liberado ao cliente
- "valor_outras_liquidacoes": valor de outras liquidações (se houver)
- "tarifa_cadastro": valor da tarifa de cadastro
- "seguro": valor do seguro (se houver)
- "valor_iof": valor do IOF
- "taxa_juros": taxa de juros nominal (%)
- "primeiro_vencimento": data do primeiro vencimento (no formato DD/MM/AAAA)
- "quantidade_parcelas": número total de parcelas
- "valor_parcela": valor de cada parcela
- "cet": Custo Efetivo Total (%)
- "data_assinatura": data de assinatura do contrato (formato DD/MM/AAAA)
- "arquivo": nome do arquivo atual (use "{nome_arquivo}")

Retorne apenas um JSON com esses campos, sem texto adicional. Segue o texto:

\"\"\"{texto}\"\"\"
"""

def extrair_json_valido(texto):
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        return match.group(0)
    return "{}"

def enviar_com_retry(prompt, max_tentativas=5):
    for tentativa in range(max_tentativas):
        try:
            return client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
        except openai.RateLimitError as e:
            tempo_espera = 10 + tentativa * 5  # espera progressiva: 10s, 15s, 20s...
            print(f"⚠️ Rate limit atingido. Tentando novamente em {tempo_espera}s...")
            time.sleep(tempo_espera)
        except Exception as e:
            raise e
    raise Exception("❌ Erro: número máximo de tentativas excedido.")

def fallback_via_ia_batch(lista_entradas):
    resultados = []

    for item in lista_entradas:
        try:
            prompt = gerar_prompt(item["texto"], item["arquivo"])
            resposta = enviar_com_retry(prompt)

            conteudo = resposta.choices[0].message.content.strip()
            json_puro = extrair_json_valido(conteudo)

            try:
                dados_extraidos = json.loads(json_puro)
            except Exception as e:
                print(f"❌ Erro ao converter JSON no arquivo {item['arquivo']}: {e}")
                continue

            dados_extraidos["arquivo"] = item["arquivo"]
            resultados.append(dados_extraidos)

            time.sleep(1.2)  # pausa leve entre chamadas para evitar pico

        except Exception as e:
            print(f"❌ Erro no arquivo {item['arquivo']}: {e}")

    return resultados
