# 🧠 OCR CCB - Extração Inteligente de Dados de Cédulas de Crédito Bancário

Este projeto automatiza a extração de dados de contratos do tipo **CCB (Cédula de Crédito Bancário)** a partir de arquivos PDF, utilizando **IA (GPT-3.5 via OpenAI)** e integração com o **Google Sheets**.

## 📌 Funcionalidades

- ✅ Leitura automática de contratos CCB em PDF  
- ✅ Extração inteligente com IA (OpenAI)  
- ✅ Limpeza e estruturação do texto extraído  
- ✅ Controle de duplicidade (evita processar o mesmo arquivo)  
- ✅ Registro automático dos dados extraídos no Google Sheets  
- ✅ Compatível com lote de milhares de arquivos  
- ✅ Sistema de fallback robusto com retry automático em caso de erros  

## 📁 Estrutura do Projeto

```
OCR-CCBs/
├── main.py
├── fallback_via_ia.py
├── .env
├── credentials.json
├── requirements.txt
└── README.md
```

## ⚙️ Requisitos

- Python 3.10+
- Conta na [OpenAI](https://platform.openai.com/)
- Conta de serviço no Google Cloud com acesso ao Google Sheets
- Acesso à API do Google Sheets
- Chave da API da OpenAI

## 📦 Instalação

1. Clone o repositório:

```bash
git clone https://github.com/bitguardian/CCBot-IA.git
cd CCBot-IA
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` com a seguinte variável:

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

4. Ajuste o caminho da pasta com os PDFs no `main.py`:

```python
PASTA_PDFS = r"CAMINHO/DA/PASTA/COM/PDFS"
```

5. Configure o nome da planilha e aba:

```python
NOME_PLANILHA = "OCR CCB"
NOME_ABA = "Página1"
```

6. Com tudo configurado, execute:

```bash
python main.py
```

## 📋 Campos extraídos

A IA irá extrair os seguintes campos de cada contrato:

- número da proposta
- nome do cliente
- valor total do contrato
- valor liberado
- outras liquidações
- tarifa de cadastro
- seguro
- valor do IOF
- taxa de juros mensal
- taxa de juros anual
- primeiro vencimento
- quantidade de parcelas
- valor de cada parcela
- CET
- data de assinatura
- nome do arquivo
- tipo de documento (ccb)
- método de extração (fallback_ia)

## 📌 Exemplo de saída esperada no Google Sheets

| Proposta | Cliente | Valor Total | Valor Liberado | ... | Arquivo | Tipo | Método |
|----------|---------|-------------|----------------|-----|---------|------|--------|
| 123456   | João S. | R$ 10.000   | R$ 9.500       | ... | doc.pdf | ccb  | fallback_ia |

## 🧠 Como funciona a extração por IA?

O arquivo `fallback_via_ia.py` monta um prompt orientado para o modelo GPT-3.5-turbo da OpenAI, pedindo a extração dos campos em formato JSON. A resposta é validada e processada para posterior inclusão na planilha.

## ⚠️ Observações importantes

- A IA pode falhar se o texto do PDF estiver muito danificado.
- A API da OpenAI possui limites de uso e pode gerar custos. Verifique sua conta.