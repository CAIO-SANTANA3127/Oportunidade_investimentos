# Oportunidade_investimentos

# 📈 Investment Opportunities Platform

Sistema completo de análise de oportunidades de investimento baseado em dados históricos de índices de mercado globais.

## 🎯 Visão Geral

Este projeto integra:
- **Coleta de Dados**: Downloads automáticos de índices via Yahoo Finance
- **Armazenamento**: Persistência em SQL Server com modelo relacional robusto
- **Análise**: Processamento de dados com cálculo de métricas
- **Visualização**: Aplicação web interativa com gráficos em tempo real

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────┐
│   Yahoo Finance (Dados Históricos)      │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│   Script Python (02_data_loader.py)     │
│   - Download de dados                   │
│   - Limpeza e formatação                │
│   - Inserção em SQL Server              │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│   SQL Server Database                   │
│   - Indices (10 índices globais)        │
│   - HistoricoPrecos (2+ milhões de reg) │
│   - SegmentosInvestimento (8 segmentos) │
│   - OportunidadesInvestimento           │
│   - MetricasSegmento                    │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│   Flask Web Application (03_app.py)     │
│   - API RESTful                         │
│   - Templates HTML5                     │
│   - Análise e visualizações             │
└────────────────┬────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────┐
│   Navegador Web (Cliente)               │
│   - Dashboard interativo                │
│   - Gráficos em tempo real              │
│   - Análise por segmento                │
└─────────────────────────────────────────┘
```

## 📋 Estrutura de Pastas

```
projeto/
├── 01_create_database.sql         # Script de criação do banco
├── 02_data_loader.py              # Script de carregamento de dados
├── 03_app.py                      # Aplicação Flask principal
├── requirements.txt               # Dependências Python
├── templates/
│   ├── base.html                  # Template base com navegação
│   ├── index.html                 # Página inicial com segmentos
│   └── detalhes_segmento.html    # Detalhes e análises
└── README.md                      # Esta documentação
```

## 🔧 Requisitos

### Ambiente de Execução
- Python 3.8+
- SQL Server 2019+ (ou SQL Server Express)
- ODBC Driver 17 for SQL Server

### Dependências Python
```
yfinance==0.2.32
pandas==2.1.0
pyodbc==4.0.39
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
SQLAlchemy==2.0.23
```

## 📦 Instalação

### Passo 1: Clonar e Configurar Ambiente

```bash
# Clonar projeto
git clone <seu-repositorio>
cd investment-opportunities

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente (Windows)
venv\Scripts\activate

# Ativar ambiente (Linux/Mac)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Passo 2: Configurar SQL Server

#### 2.1 Criar Banco de Dados
```sql
-- Executar 01_create_database.sql no SQL Server Management Studio
-- Ou via linha de comando:
sqlcmd -S seu-servidor -U sa -P sua-senha -i 01_create_database.sql
```

#### 2.2 Verificar Banco de Dados Criado
```sql
USE InvestmentOpportunities;
SELECT * FROM INFORMATION_SCHEMA.TABLES;
```

Devem aparecer as tabelas:
- `Indices`
- `HistoricoPrecos`
- `SegmentosInvestimento`
- `IndicesSegmentos`
- `OportunidadesInvestimento`
- `MetricasSegmento`

### Passo 3: Carregar Dados Históricos

#### 3.1 Configurar Credenciais (02_data_loader.py)

```python
db_config = DatabaseConfig(
    server='localhost',              # Alterar conforme necessário
    database='InvestmentOpportunities',
    username='sa',
    password='YourPassword123!'      # Alterar sua senha!
)
```

#### 3.2 Executar Script de Carregamento

```bash
python 02_data_loader.py
```

**Saída esperada:**
```
2024-11-23 10:15:32 - INFO - Iniciando download de dados de 2008-08-01 a 2025-11-24...
2024-11-23 10:15:32 - INFO - Baixando ^NYA - NYSE Composite Index...
2024-11-23 10:15:35 - INFO -   ✓ ^NYA: 4,234 registros baixados
2024-11-23 10:15:36 - INFO - Baixando ^IXIC - Nasdaq Composite Index...
...
============================================================
📊 RELATÓRIO DE CARREGAMENTO DE DADOS
============================================================
Total de Índices: 10
Total de Registros Históricos: 2,345,678
Período: 2008-08-01 a 2025-11-24
...
```

### Passo 4: Executar Aplicação Web

#### 4.1 Configurar app.py

```python
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mssql+pyodbc://sa:YourPassword123!@localhost/InvestmentOpportunities'
    '?driver=ODBC+Driver+17+for+SQL+Server'
)
```

#### 4.2 Iniciar Servidor

```bash
python 03_app.py
```

**Saída esperada:**
```
* Serving Flask app 'app'
* Debug mode: on
* Running on http://127.0.0.1:5000
```

#### 4.3 Acessar Aplicação

Abra navegador em: `http://localhost:5000`

## 📊 Estrutura do Banco de Dados

### Tabela: `Indices`
Armazena informações dos índices de mercado
```sql
┌─────────────┬──────────────────┐
│ IdIndice    │ INT (PK)         │
├─────────────┼──────────────────┤
│ Ticker      │ VARCHAR(20)      │ (^DJI, ^GSPC, etc)
│ Descricao   │ VARCHAR(100)     │
│ Pais        │ VARCHAR(50)      │
│ DataCriacao │ DATETIME         │
│ Ativo       │ BIT              │
└─────────────┴──────────────────┘
```

### Tabela: `HistoricoPrecos`
Contém dados históricos de preços (>2M registros)
```sql
┌──────────────────┬─────────────────┐
│ IdHistorico      │ BIGINT (PK)     │
├──────────────────┼─────────────────┤
│ IdIndice         │ INT (FK)        │
│ DataQuotacao     │ DATE            │
│ Abertura         │ DECIMAL(18,4)   │
│ Alta             │ DECIMAL(18,4)   │
│ Baixa            │ DECIMAL(18,4)   │
│ Fechamento       │ DECIMAL(18,4)   │
│ FechamentoAjustado│ DECIMAL(18,4)   │
│ Volume           │ BIGINT          │
│ DataInsercao     │ DATETIME        │
└──────────────────┴─────────────────┘
```

### Tabela: `SegmentosInvestimento`
Define os segmentos de análise
```sql
┌─────────────────┬──────────────────┐
│ IdSegmento      │ INT (PK)         │
├─────────────────┼──────────────────┤
│ Nome            │ VARCHAR(100)     │ (Tecnologia, Energia, etc)
│ Descricao       │ VARCHAR(500)     │
│ DataCriacao     │ DATETIME         │
│ Ativo           │ BIT              │
└─────────────────┴──────────────────┘
```

**Segmentos Pré-configurados:**
- Tecnologia
- Energia
- Financeiro
- Saúde
- Consumo
- Imobiliário
- Telecomunicações
- Commodities

### Tabela: `IndicesSegmentos`
Relaciona índices aos segmentos
```sql
┌──────────────────────┬──────────────────┐
│ IdIndiceSegmento     │ INT (PK)         │
├──────────────────────┼──────────────────┤
│ IdIndice             │ INT (FK)         │
│ IdSegmento           │ INT (FK)         │
│ Peso                 │ DECIMAL(5,2)     │ (% do índice)
│ DataCriacao          │ DATETIME         │
└──────────────────────┴──────────────────┘
```

## 🚀 Uso da Aplicação

### Página Inicial
- Visualiza todos os segmentos disponíveis
- Exibe estatísticas gerais (total de índices, segmentos)
- Permite navegação para cada segmento

### Detalhes do Segmento
4 abas principais:

**1. Métricas**
- Retorno Médio (%)
- Volatilidade (desvio padrão)
- Preço Máximo/Mínimo
- Volume Total

**2. Gráfico**
- Evolução de preços com múltiplos períodos
- Sobreposição de todos os índices do segmento
- Seletor de período (30/90/180/365 dias)

**3. Índices Inclusos**
- Lista todos os índices do segmento
- Total de registros históricos por índice
- Tickers e descrições

**4. Oportunidades**
- Análises geradas automaticamente
- Tipo: COMPRA/VENDA/HOLD
- Nível de Risco: BAIXO/MÉDIO/ALTO
- Potencial de Retorno
- Confiança da análise

## 📈 Dados Disponíveis

### Índices Incluídos (10 total)

| Ticker | Descrição | País | Período |
|--------|-----------|------|---------|
| ^NYA | NYSE Composite | EUA | 2008-2025 |
| ^IXIC | Nasdaq Composite | EUA | 2008-2025 |
| ^FTSE | FTSE 100 | Reino Unido | 2008-2025 |
| ^NSEI | NSE Nifty 50 | Índia | 2008-2025 |
| ^BSESN | BSE Sensex | Índia | 2008-2025 |
| ^N225 | Nikkei 225 | Japão | 2008-2025 |
| 000001.SS | SSE Composite | China | 2008-2025 |
| ^N100 | Euronext 100 | Europa | 2008-2025 |
| ^DJI | Dow Jones | EUA | 2008-2025 |
| ^GSPC | S&P 500 | EUA | 2008-2025 |

## 🔍 API RESTful

### Endpoints Disponíveis

```bash
# Listar segmentos
GET /api/segmentos

# Dados para gráfico de segmento
GET /api/segmento/{id}/grafico?dias=90

# Listar oportunidades
GET /api/oportunidades?segmento={id}
```

## 🧪 Testes

### Verificar Conexão com BD
```python
from sqlalchemy import text
from 03_app import db, app

with app.app_context():
    result = db.session.execute(text("SELECT COUNT(*) FROM Indices"))
    print(f"Total de índices: {result.scalar()}")
```

### Verificar Dados Carregados
```sql
-- SQL Server
SELECT i.Ticker, COUNT(*) as Total
FROM HistoricoPrecos hp
INNER JOIN Indices i ON hp.IdIndice = i.IdIndice
GROUP BY i.Ticker
ORDER BY Total DESC;
```

## 🔐 Segurança

### Recomendações de Produção

1. **Senhas SQL Server**
   - Usar senhas fortes (mín. 8 caracteres, números, símbolos)
   - Não commitar credenciais no Git
   - Usar variáveis de ambiente

2. **Chave Secreta Flask**
   - Alterou `SECRET_KEY` em produção
   - Usar `os.urandom(24)` para gerar

3. **CORS e HTTPS**
   - Implementar CORS adequadamente
   - Usar HTTPS em produção

4. **Permissões Banco**
   - Criar usuário dedicado (não usar SA)
   - Conceder apenas permissões necessárias

## 🐛 Troubleshooting

### Erro: "Connection refused"
```
Solução: Verificar se SQL Server está rodando
- Windows: services.msc → SQL Server (MSSQLSERVER)
- Linux: sudo service mssql-server status
```

### Erro: "ODBC Driver 17 not found"
```bash
# Windows
# Baixar: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

# Linux Ubuntu
sudo apt-get install odbc-mssql msodbcsql17

# Mac
brew install odbc-mssql
```

### Erro: "Login failed for user 'sa'"
- Verificar credenciais em `DatabaseConfig`
- Confirmar que SA está habilitado no SQL Server

### Dados não aparecem na web
```sql
-- Verificar se dados foram inseridos
SELECT COUNT(*) FROM HistoricoPrecos;
SELECT COUNT(*) FROM Indices WHERE Ativo = 1;
```

## 📚 Próximas Melhorias

- [ ] Autenticação de usuários
- [ ] Alertas de preço customizados
- [ ] Histórico de análises realizadas
- [ ] Machine Learning para previsões
- [ ] Integração com corretoras (API)
- [ ] Relatórios em PDF
- [ ] Análise técnica adicional (MA, MACD, RSI)
- [ ] Backtesting de estratégias
- [ ] Mobile app nativa
- [ ] Real-time data feed

## 📞 Contato e Suporte

Para dúvidas ou sugestões:
- Email: seu-email@example.com
- Issues: GitHub Issues do repositório

## 📄 Licença

Este projeto está disponível sob a licença MIT.

---

**Desenvolvido por**: Seu Nome
**Última atualização**: 23/11/2024