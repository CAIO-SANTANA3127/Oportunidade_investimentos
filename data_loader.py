import yfinance as yf
import pandas as pd
import pyodbc
from datetime import datetime
import logging

# =====================================================
# CONFIGURAÇÃO DE LOGGING
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# =====================================================
class DatabaseConfig:
    """Classe para gerenciar configurações de conexão com SQL Server"""
    
    def __init__(self, server='localhost', database='InvestmentOpportunities', 
                 username='sa', password='YourPassword123!'):
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver = '{ODBC Driver 17 for SQL Server}'
    
    def get_connection_string(self):
        """Retorna string de conexão para SQL Server"""
        return f'Driver={self.driver};Server={self.server};Database={self.database};UID={self.username};PWD={self.password}'
    
    def get_connection(self):
        """Cria e retorna uma conexão com o banco de dados"""
        try:
            conn = pyodbc.connect(self.get_connection_string())
            logger.info("✓ Conexão com SQL Server estabelecida")
            return conn
        except pyodbc.Error as e:
            logger.error(f"✗ Erro ao conectar ao SQL Server: {e}")
            raise

# =====================================================
# CLASSE PARA GERENCIAR DADOS DE ÍNDICES
# =====================================================
class IndiceManager:
    """Gerencia operações com índices de mercado"""
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.tickers_info = {
            '^NYA': {'Descricao': 'NYSE Composite Index', 'Pais': 'Estados Unidos'},
            '^IXIC': {'Descricao': 'Nasdaq Composite Index', 'Pais': 'Estados Unidos'},
            '^FTSE': {'Descricao': 'FTSE 100 Index', 'Pais': 'Reino Unido'},
            '^NSEI': {'Descricao': 'NSE Nifty 50 Index', 'Pais': 'Índia'},
            '^BSESN': {'Descricao': 'BSE Sensex Index', 'Pais': 'Índia'},
            '^N225': {'Descricao': 'Nikkei 225 Index', 'Pais': 'Japão'},
            '000001.SS': {'Descricao': 'SSE Composite Index', 'Pais': 'China'},
            '^N100': {'Descricao': 'Euronext 100 Index', 'Pais': 'Europa'},
            '^DJI': {'Descricao': 'Dow Jones Industrial Average', 'Pais': 'Estados Unidos'},
            '^GSPC': {'Descricao': 'S&P 500 Index', 'Pais': 'Estados Unidos'}
        }
    
    def baixar_dados_indices(self, start_date='2008-08-01', end_date='2025-11-24'):
        """Baixa dados históricos de todos os índices"""
        dados_completos = []
        
        logger.info(f"Iniciando download de dados de {start_date} a {end_date}...\n")
        
        for ticker, info in self.tickers_info.items():
            logger.info(f"Baixando {ticker} - {info['Descricao']}...")
            try:
                df = yf.download(ticker, start=start_date, end=end_date, 
                               progress=False, auto_adjust=False)
                
                if not df.empty:
                    df = df.reset_index()
                    
                    # Achatar colunas se for MultiIndex
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    # Renomear Adj Close
                    if 'Adj Close' not in df.columns:
                        for col in df.columns:
                            if 'adj' in str(col).lower() and 'close' in str(col).lower():
                                df.rename(columns={col: 'Adj Close'}, inplace=True)
                                break
                    
                    df['Ticker'] = ticker
                    df['Descricao'] = info['Descricao']
                    df['Pais'] = info['Pais']
                    
                    # Renomear colunas para padrão SQL
                    df = df.rename(columns={
                        'Date': 'DataQuotacao',
                        'Open': 'Abertura',
                        'High': 'Alta',
                        'Low': 'Baixa',
                        'Close': 'Fechamento',
                        'Adj Close': 'FechamentoAjustado',
                        'Volume': 'Volume'
                    })
                    
                    colunas_mantidas = ['Ticker', 'Descricao', 'Pais', 'DataQuotacao', 
                                      'Abertura', 'Alta', 'Baixa', 'Fechamento', 
                                      'FechamentoAjustado', 'Volume']
                    
                    df = df[colunas_mantidas]
                    dados_completos.append(df)
                    logger.info(f"  ✓ {ticker}: {len(df)} registros baixados")
                else:
                    logger.warning(f"  ✗ {ticker}: Sem dados disponíveis")
                    
            except Exception as e:
                logger.error(f"  ✗ Erro em {ticker}: {str(e)}")
        
        if dados_completos:
            df_final = pd.concat(dados_completos, ignore_index=True)
            logger.info(f"\n📊 Total de registros antes de limpeza: {len(df_final):,}")
            return df_final
        else:
            logger.error("❌ Nenhum dado foi baixado")
            return None
    
    def salvar_em_csv(self, df, filename='indices_mercado_2008_2025.csv'):
        """Salva dados em CSV"""
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"✓ Arquivo CSV salvo: {filename}")
            return filename
        except Exception as e:
            logger.error(f"✗ Erro ao salvar CSV: {e}")
            raise

# =====================================================
# CLASSE PARA OPERAÇÕES COM SQL SERVER
# =====================================================
class RepositorioSQLServer:
    """Gerencia operações de persistência em SQL Server"""
    
    def __init__(self, db_config):
        self.db_config = db_config
    
    def insere_ou_atualiza_indice(self, df):
        """Insere ou atualiza informações de índices"""
        conn = self.db_config.get_connection()
        cursor = conn.cursor()
        
        indices_unicos = df[['Ticker', 'Descricao', 'Pais']].drop_duplicates()
        
        logger.info(f"Inserindo/atualizando {len(indices_unicos)} índices...")
        
        for _, row in indices_unicos.iterrows():
            try:
                cursor.execute('''
                    IF NOT EXISTS (SELECT 1 FROM Indices WHERE Ticker = ?)
                    BEGIN
                        INSERT INTO Indices (Ticker, Descricao, Pais)
                        VALUES (?, ?, ?)
                    END
                ''', row['Ticker'], row['Ticker'], row['Descricao'], row['Pais'])
                
            except Exception as e:
                logger.error(f"Erro ao inserir índice {row['Ticker']}: {e}")
        
        conn.commit()
        logger.info("✓ Índices processados com sucesso")
        cursor.close()
    
    def insere_historico_precos(self, df):
        """Insere dados históricos de preços"""
        conn = self.db_config.get_connection()
        cursor = conn.cursor()
        
        logger.info(f"Inserindo {len(df)} registros de preços...")
        
        # Buscar IDs dos índices
        cursor.execute("SELECT IdIndice, Ticker FROM Indices")
        indices_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        registros_inseridos = 0
        registros_duplicados = 0
        
        for _, row in df.iterrows():
            try:
                id_indice = indices_map.get(row['Ticker'])
                if not id_indice:
                    logger.warning(f"Índice {row['Ticker']} não encontrado")
                    continue
                
                data_quotacao = pd.to_datetime(row['DataQuotacao']).date()
                
                cursor.execute('''
                    IF NOT EXISTS (SELECT 1 FROM HistoricoPrecos 
                                 WHERE IdIndice = ? AND DataQuotacao = ?)
                    BEGIN
                        INSERT INTO HistoricoPrecos 
                        (IdIndice, DataQuotacao, Abertura, Alta, Baixa, Fechamento, FechamentoAjustado, Volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    END
                ''', id_indice, data_quotacao, id_indice, data_quotacao,
                    row['Abertura'], row['Alta'], row['Baixa'], 
                    row['Fechamento'], row['FechamentoAjustado'], int(row['Volume']))
                
                if cursor.rowcount > 0:
                    registros_inseridos += 1
                else:
                    registros_duplicados += 1
                    
            except Exception as e:
                logger.error(f"Erro ao inserir preço: {e}")
        
        conn.commit()
        logger.info(f"✓ {registros_inseridos} registros inseridos, {registros_duplicados} duplicados")
        cursor.close()
        conn.close()
    
    def vincular_indices_segmentos(self):
        """Vincula índices aos segmentos apropriados"""
        conn = self.db_config.get_connection()
        cursor = conn.cursor()
        
        # Mapeamento de tickers para segmentos
        ticker_segmento = {
            '^IXIC': 'Tecnologia',      # Nasdaq = Tech
            '^N100': 'Tecnologia',      # Euronext 100 = Tech heavy
            '000001.SS': 'Tecnologia',  # China = Tech
        }
        
        logger.info("Vinculando índices aos segmentos...")
        
        for ticker, segmento in ticker_segmento.items():
            try:
                cursor.execute('''
                    IF NOT EXISTS (SELECT 1 FROM IndicesSegmentos 
                                 WHERE IdIndice = (SELECT IdIndice FROM Indices WHERE Ticker = ?)
                                 AND IdSegmento = (SELECT IdSegmento FROM SegmentosInvestimento WHERE Nome = ?))
                    BEGIN
                        INSERT INTO IndicesSegmentos (IdIndice, IdSegmento)
                        SELECT IdIndice FROM Indices WHERE Ticker = ?,
                               (SELECT IdSegmento FROM SegmentosInvestimento WHERE Nome = ?)
                    END
                ''', ticker, segmento, ticker, segmento)
                
            except Exception as e:
                logger.error(f"Erro ao vincular {ticker} a {segmento}: {e}")
        
        conn.commit()
        logger.info("✓ Segmentos vinculados com sucesso")
        cursor.close()
        conn.close()
    
    def gera_relatorio_carregamento(self):
        """Gera relatório do carregamento de dados"""
        conn = self.db_config.get_connection()
        cursor = conn.cursor()
        
        logger.info("\n" + "="*60)
        logger.info("📊 RELATÓRIO DE CARREGAMENTO DE DADOS")
        logger.info("="*60)
        
        # Total de índices
        cursor.execute("SELECT COUNT(*) FROM Indices WHERE Ativo = 1")
        total_indices = cursor.fetchone()[0]
        logger.info(f"Total de Índices: {total_indices}")
        
        # Total de registros históricos
        cursor.execute("SELECT COUNT(*) FROM HistoricoPrecos")
        total_historico = cursor.fetchone()[0]
        logger.info(f"Total de Registros Históricos: {total_historico:,}")
        
        # Período de dados
        cursor.execute("""
            SELECT MIN(DataQuotacao), MAX(DataQuotacao) 
            FROM HistoricoPrecos
        """)
        min_date, max_date = cursor.fetchone()
        logger.info(f"Período: {min_date} a {max_date}")
        
        # Registros por índice
        logger.info("\nRegistros por Índice:")
        cursor.execute("""
            SELECT i.Ticker, i.Descricao, COUNT(*) as Total
            FROM Indices i
            LEFT JOIN HistoricoPrecos hp ON i.IdIndice = hp.IdIndice
            GROUP BY i.IdIndice, i.Ticker, i.Descricao
            ORDER BY Total DESC
        """)
        
        for ticker, desc, total in cursor.fetchall():
            logger.info(f"  {ticker:12} - {desc:35} : {total:,} registros")
        
        cursor.close()
        conn.close()
        logger.info("="*60 + "\n")

# =====================================================
# EXECUÇÃO PRINCIPAL
# =====================================================
def main():
    """Função principal do script"""
    
    try:
        # Configurar banco de dados
        db_config = DatabaseConfig(
            server='localhost',
            database='InvestmentOpportunities',
            username='sa',
            password='YourPassword123!'  # ALTERAR CONFORME SEU AMBIENTE
        )
        
        # Etapa 1: Baixar dados
        indice_manager = IndiceManager(db_config)
        df_indices = indice_manager.baixar_dados_indices()
        
        if df_indices is None:
            logger.error("Falha ao baixar dados")
            return
        
        # Etapa 2: Salvar em CSV (backup)
        csv_file = indice_manager.salvar_em_csv(df_indices)
        
        # Etapa 3: Inserir no SQL Server
        repositorio = RepositorioSQLServer(db_config)
        repositorio.insere_ou_atualiza_indice(df_indices)
        repositorio.insere_historico_precos(df_indices)
        repositorio.vincular_indices_segmentos()
        
        # Etapa 4: Gerar relatório
        repositorio.gera_relatorio_carregamento()
        
        logger.info("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
        
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        raise

if __name__ == "__main__":
    main()