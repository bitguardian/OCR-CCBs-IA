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
Você é um especialista em contratos bancários. Leia o texto a seguir e extraia os dados **exatamente** como solicitado abaixo, mesmo que as expressões no texto sejam diferentes.

🎯 Retorne **apenas um JSON** com os seguintes campos:

- "numero_proposta": número do contrato ou da proposta. Ele sempre aparece depois de expressões como "Proposta nº", "Nº do Contrato", "Contrato nº", "Nº do Instrumento", "CCB nº" ou similares. Extraia apenas o número — **não inclua palavras como "Proposta", "Contrato" ou "Nº" no valor final**.
- "nome_cliente": nome completo da pessoa contratante
- "cpf_cliente": CPF do cliente - exemplo: 123.456.789-00 (sem formatação, apenas números)
- "valor_total": valor total financiado (inclui juros e encargos) — exemplo: R$ 9.000,00
- "valor_liberado": valor líquido recebido pelo cliente — exemplo: R$ 8.500,00
- "valor_outras_liquidacoes": outras liquidações, se houver
- "tarifa_cadastro": valor da tarifa de cadastro, se houver
- "seguro": valor do seguro, se houver
- "valor_iof": valor do IOF, se houver
- "taxa_juros_mensal": taxa de juros nominal ao mês — ex: 2,5% ao mês
- "taxa_juros_anual": taxa de juros nominal ao ano — ex: 36% ao ano
- "primeiro_vencimento": data da primeira parcela — ex: 20/03/2023
- "quantidade_parcelas": número total de parcelas — ex: 96
- "valor_parcela": valor de cada parcela — ex: R$ 125,90
- "cet": custo efetivo total (CET) extrair taxa mensal e anual, se houver — ex: 2,6% ao mês e 36,07% ao ano
- "data_assinatura": data em que o contrato foi assinado. Pode aparecer de várias formas, como:
- "Assinado eletronicamente por..."
- "Assinatura em"
- "Assinado em"

Mesmo que a data esteja escrita por extenso (ex: "5 de outubro de 2022"), converta sempre para o formato DD/MM/AAAA (ex: "05/10/2022"), extraia exatamente a data em que o documento foi assinado, não a data de emissão, ou outra data qualquer.
- "arquivo": nome do arquivo atual (use exatamente: {nome_arquivo})

⚠️ Observações:
- Sempre que houver taxa mensal **e** anual, extraia as duas (ex: 2,6% ao mês e 36,07% ao ano).
- Se os valores forem escritos de formas diferentes (ex: "valor liberado ao cliente", "seguro prestamista", "tarifa de abertura"), adapte e extraia corretamente.
- Retorne todos os valores **no formato R$ XX.XXX,XX**, mesmo que o original esteja diferente.
- Se algum valor não estiver presente, retorne-o como string vazia ("").

📄 Texto do contrato:
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

def corrigir_dados(dados):
    campos_valor = [
        "valor_total", "valor_liberado", "valor_outras_liquidacoes",
        "tarifa_cadastro", "seguro", "valor_iof", "valor_parcela"
    ]

    for campo in campos_valor:
        valor = dados.get(campo, "")
        if isinstance(valor, str):
            valor = valor.strip()
            if valor and not valor.startswith("R$"):
                valor = "R$ " + valor
            dados[campo] = valor
        else:
            dados[campo] = ""

    # Normalização do CPF (remove pontos e traço)
    if "cpf_cliente" in dados and isinstance(dados["cpf_cliente"], str):
        dados["cpf_cliente"] = dados["cpf_cliente"].replace(".", "").replace("-", "").strip()

    # Padroniza taxas (sem espaços desnecessários)
    for campo in ["taxa_juros_mensal", "taxa_juros_anual", "cet"]:
        if campo in dados and isinstance(dados[campo], str):
            dados[campo] = dados[campo].replace(" %", "%").strip()

    return dados

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
            dados_extraidos = corrigir_dados(dados_extraidos)
            resultados.append(dados_extraidos)

            time.sleep(1.2)  # pausa leve entre chamadas para evitar pico

        except Exception as e:
            print(f"❌ Erro no arquivo {item['arquivo']}: {e}")

    return resultados
