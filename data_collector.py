import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import logging
from typing import List, Dict
import time

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YahooFinanceCollector:
    """Coletor de dados do Yahoo Finance"""
    
    def __init__(self, connection_string: str):
        """
        Inicializa o coletor
        
        Args:
            connection_string: String de conexão do SQL Server
        """
        self.engine = create_engine(connection_string)
        self.connection_string = connection_string
        
    def adicionar_indice(self, ticker: str, descricao: str, pais: str) -> int:
        """
        Adiciona um novo índice ao banco de dados
        
        Args:
            ticker: Símbolo do ticker (ex: ^GSPC para S&P 500)
            descricao: Descrição do índice
            pais: País de origem
            
        Returns:
            ID do índice inserido
        """
        try:
            with self.engine.connect() as conn:
                # Verificar se já existe
                query = text("""
                    SELECT IdIndice FROM Indices WHERE Ticker = :ticker
                """)
                result = conn.execute(query, {'ticker': ticker}).fetchone()
                
                if result:
                    logger.info(f"✓ Índice {ticker} já existe (ID: {result[0]})")
                    return result[0]
                
                # Inserir novo índice
                insert_query = text("""
                    INSERT INTO Indices (Ticker, Descricao, Pais, DataCriacao, Ativo)
                    OUTPUT INSERTED.IdIndice
                    VALUES (:ticker, :descricao, :pais, :data_criacao, 1)
                """)
                
                result = conn.execute(insert_query, {
                    'ticker': ticker,
                    'descricao': descricao,
                    'pais': pais,
                    'data_criacao': datetime.now()
                })
                conn.commit()
                
                id_indice = result.fetchone()[0]
                logger.info(f"✓ Índice {ticker} adicionado (ID: {id_indice})")
                return id_indice
                
        except Exception as e:
            logger.error(f"✗ Erro ao adicionar índice {ticker}: {e}")
            raise
    
    def baixar_dados_historicos(self, ticker: str, periodo: str = "2y") -> pd.DataFrame:
        """
        Baixa dados históricos do Yahoo Finance
        
        Args:
            ticker: Símbolo do ticker
            periodo: Período dos dados (1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max)
            
        Returns:
            DataFrame com os dados históricos
        """
        try:
            logger.info(f"⬇ Baixando dados de {ticker} (período: {periodo})...")
            
            # Baixar dados do Yahoo Finance
            stock = yf.Ticker(ticker)
            df = stock.history(period=periodo)
            
            if df.empty:
                logger.warning(f"⚠ Nenhum dado encontrado para {ticker}")
                return pd.DataFrame()
            
            # Resetar index para ter a data como coluna
            df.reset_index(inplace=True)
            
            logger.info(f"✓ {len(df)} registros baixados para {ticker}")
            return df
            
        except Exception as e:
            logger.error(f"✗ Erro ao baixar dados de {ticker}: {e}")
            return pd.DataFrame()
    
    def salvar_historico_precos(self, id_indice: int, ticker: str, df: pd.DataFrame):
        """
        Salva dados históricos no banco de dados
        
        Args:
            id_indice: ID do índice
            ticker: Símbolo do ticker
            df: DataFrame com os dados
        """
        if df.empty:
            logger.warning(f"⚠ Nenhum dado para salvar de {ticker}")
            return
        
        try:
            with self.engine.connect() as conn:
                # Limpar dados antigos (opcional - remova se quiser manter histórico)
                # delete_query = text("DELETE FROM HistoricoPrecos WHERE IdIndice = :id_indice")
                # conn.execute(delete_query, {'id_indice': id_indice})
                
                registros_inseridos = 0
                registros_duplicados = 0
                
                for _, row in df.iterrows():
                    try:
                        # Verificar se já existe
                        check_query = text("""
                            SELECT COUNT(*) FROM HistoricoPrecos 
                            WHERE IdIndice = :id_indice AND DataQuotacao = :data
                        """)
                        
                        existe = conn.execute(check_query, {
                            'id_indice': id_indice,
                            'data': row['Date'].date()
                        }).fetchone()[0]
                        
                        if existe > 0:
                            registros_duplicados += 1
                            continue
                        
                        # Inserir registro
                        insert_query = text("""
                            INSERT INTO HistoricoPrecos (
                                IdIndice, DataQuotacao, Abertura, Alta, Baixa, 
                                Fechamento, FechamentoAjustado, Volume, DataInsercao
                            ) VALUES (
                                :id_indice, :data_quotacao, :abertura, :alta, :baixa,
                                :fechamento, :fechamento_ajustado, :volume, :data_insercao
                            )
                        """)
                        
                        conn.execute(insert_query, {
                            'id_indice': id_indice,
                            'data_quotacao': row['Date'].date(),
                            'abertura': float(row['Open']) if pd.notna(row['Open']) else None,
                            'alta': float(row['High']) if pd.notna(row['High']) else None,
                            'baixa': float(row['Low']) if pd.notna(row['Low']) else None,
                            'fechamento': float(row['Close']) if pd.notna(row['Close']) else None,
                            'fechamento_ajustado': float(row['Close']) if pd.notna(row['Close']) else None,
                            'volume': int(row['Volume']) if pd.notna(row['Volume']) else 0,
                            'data_insercao': datetime.now()
                        })
                        
                        registros_inseridos += 1
                        
                    except Exception as e:
                        logger.error(f"✗ Erro ao inserir registro: {e}")
                        continue
                
                conn.commit()
                logger.info(f"✓ {registros_inseridos} novos registros inseridos para {ticker}")
                if registros_duplicados > 0:
                    logger.info(f"⚠ {registros_duplicados} registros duplicados ignorados")
                
        except Exception as e:
            logger.error(f"✗ Erro ao salvar histórico de {ticker}: {e}")
            raise
    
    def coletar_indice_completo(self, ticker: str, descricao: str, pais: str, periodo: str = "2y"):
        """
        Processo completo: adiciona índice e coleta dados históricos
        
        Args:
            ticker: Símbolo do ticker
            descricao: Descrição do índice
            pais: País de origem
            periodo: Período dos dados
        """
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 Iniciando coleta: {ticker} - {descricao}")
            logger.info(f"{'='*60}")
            
            # 1. Adicionar/obter índice
            id_indice = self.adicionar_indice(ticker, descricao, pais)
            
            # 2. Baixar dados do Yahoo Finance
            df = self.baixar_dados_historicos(ticker, periodo)
            
            # 3. Salvar no banco de dados
            if not df.empty:
                self.salvar_historico_precos(id_indice, ticker, df)
                logger.info(f"✓ Coleta concluída com sucesso para {ticker}\n")
            else:
                logger.warning(f"⚠ Nenhum dado coletado para {ticker}\n")
                
        except Exception as e:
            logger.error(f"✗ Erro na coleta de {ticker}: {e}\n")
    
    def criar_segmento(self, nome: str, descricao: str) -> int:
        """
        Cria um novo segmento de investimento
        
        Args:
            nome: Nome do segmento
            descricao: Descrição do segmento
            
        Returns:
            ID do segmento criado
        """
        try:
            with self.engine.connect() as conn:
                # Verificar se já existe
                query = text("SELECT IdSegmento FROM SegmentosInvestimento WHERE Nome = :nome")
                result = conn.execute(query, {'nome': nome}).fetchone()
                
                if result:
                    logger.info(f"✓ Segmento '{nome}' já existe (ID: {result[0]})")
                    return result[0]
                
                # Inserir novo segmento
                insert_query = text("""
                    INSERT INTO SegmentosInvestimento (Nome, Descricao, DataCriacao, Ativo)
                    OUTPUT INSERTED.IdSegmento
                    VALUES (:nome, :descricao, :data_criacao, 1)
                """)
                
                result = conn.execute(insert_query, {
                    'nome': nome,
                    'descricao': descricao,
                    'data_criacao': datetime.now()
                })
                conn.commit()
                
                id_segmento = result.fetchone()[0]
                logger.info(f"✓ Segmento '{nome}' criado (ID: {id_segmento})")
                return id_segmento
                
        except Exception as e:
            logger.error(f"✗ Erro ao criar segmento '{nome}': {e}")
            raise
    
    def associar_indice_segmento(self, ticker: str, id_segmento: int, peso: float = 100.0):
        """
        Associa um índice a um segmento
        
        Args:
            ticker: Símbolo do ticker
            id_segmento: ID do segmento
            peso: Peso do índice no segmento (padrão: 100%)
        """
        try:
            with self.engine.connect() as conn:
                # Obter ID do índice
                query = text("SELECT IdIndice FROM Indices WHERE Ticker = :ticker")
                result = conn.execute(query, {'ticker': ticker}).fetchone()
                
                if not result:
                    logger.error(f"✗ Índice {ticker} não encontrado")
                    return
                
                id_indice = result[0]
                
                # Verificar se já existe associação
                check_query = text("""
                    SELECT COUNT(*) FROM IndicesSegmentos 
                    WHERE IdIndice = :id_indice AND IdSegmento = :id_segmento
                """)
                
                existe = conn.execute(check_query, {
                    'id_indice': id_indice,
                    'id_segmento': id_segmento
                }).fetchone()[0]
                
                if existe > 0:
                    logger.info(f"⚠ Índice {ticker} já associado ao segmento")
                    return
                
                # Inserir associação
                insert_query = text("""
                    INSERT INTO IndicesSegmentos (IdIndice, IdSegmento, Peso, DataCriacao)
                    VALUES (:id_indice, :id_segmento, :peso, :data_criacao)
                """)
                
                conn.execute(insert_query, {
                    'id_indice': id_indice,
                    'id_segmento': id_segmento,
                    'peso': peso,
                    'data_criacao': datetime.now()
                })
                conn.commit()
                
                logger.info(f"✓ Índice {ticker} associado ao segmento")
                
        except Exception as e:
            logger.error(f"✗ Erro ao associar índice {ticker}: {e}")

# =====================================================
# FUNÇÃO PRINCIPAL PARA EXECUTAR A COLETA
# =====================================================
def executar_coleta_completa():
    """Executa coleta completa de dados"""
    
    # String de conexão
    connection_string = (
        "mssql+pyodbc://@CAIO\\SQLEXPRESS/InvestmentOpportunities?"
        "driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    )
    
    # Criar coletor
    collector = YahooFinanceCollector(connection_string)
    
    logger.info("\n" + "="*60)
    logger.info("🚀 INICIANDO COLETA DE DADOS DO YAHOO FINANCE")
    logger.info("="*60 + "\n")
    
    # ================================================
    # DEFINIR ÍNDICES PARA COLETAR
    # ================================================
    indices_para_coletar = [
        # Índices Americanos
        {
            'ticker': '^GSPC',
            'descricao': 'S&P 500',
            'pais': 'Estados Unidos',
            'segmento': 'Mercado Amplo - EUA'
        },
        {
            'ticker': '^DJI',
            'descricao': 'Dow Jones Industrial Average',
            'pais': 'Estados Unidos',
            'segmento': 'Mercado Amplo - EUA'
        },
        {
            'ticker': '^IXIC',
            'descricao': 'NASDAQ Composite',
            'pais': 'Estados Unidos',
            'segmento': 'Tecnologia'
        },
        {
            'ticker': '^RUT',
            'descricao': 'Russell 2000',
            'pais': 'Estados Unidos',
            'segmento': 'Small Caps - EUA'
        },
        
        # Setoriais - Tecnologia
        {
            'ticker': 'XLK',
            'descricao': 'Technology Select Sector SPDR Fund',
            'pais': 'Estados Unidos',
            'segmento': 'Tecnologia'
        },
        
        # Setoriais - Energia
        {
            'ticker': 'XLE',
            'descricao': 'Energy Select Sector SPDR Fund',
            'pais': 'Estados Unidos',
            'segmento': 'Energia'
        },
        
        # Setoriais - Financeiro
        {
            'ticker': 'XLF',
            'descricao': 'Financial Select Sector SPDR Fund',
            'pais': 'Estados Unidos',
            'segmento': 'Financeiro'
        },
        
        # Setoriais - Saúde
        {
            'ticker': 'XLV',
            'descricao': 'Health Care Select Sector SPDR Fund',
            'pais': 'Estados Unidos',
            'segmento': 'Saúde'
        },
        
        # Setoriais - Consumo
        {
            'ticker': 'XLY',
            'descricao': 'Consumer Discretionary Select Sector SPDR Fund',
            'pais': 'Estados Unidos',
            'segmento': 'Consumo Discricionário'
        },
        
        # Internacional
        {
            'ticker': 'EWZ',
            'descricao': 'iShares MSCI Brazil ETF',
            'pais': 'Brasil',
            'segmento': 'Mercados Emergentes'
        },
        {
            'ticker': '^BVSP',
            'descricao': 'Ibovespa',
            'pais': 'Brasil',
            'segmento': 'Mercado Amplo - Brasil'
        },
    ]
    
    # ================================================
    # CRIAR SEGMENTOS
    # ================================================
    segmentos_info = {
        'Mercado Amplo - EUA': 'Índices amplos do mercado americano',
        'Tecnologia': 'Empresas de tecnologia e inovação',
        'Energia': 'Setor de energia, petróleo e gás',
        'Financeiro': 'Bancos e instituições financeiras',
        'Saúde': 'Farmacêuticas e biotecnologia',
        'Consumo Discricionário': 'Varejo e bens de consumo',
        'Small Caps - EUA': 'Empresas de pequena capitalização',
        'Mercados Emergentes': 'Mercados em desenvolvimento',
        'Mercado Amplo - Brasil': 'Índices amplos do mercado brasileiro'
    }
    
    segmentos_ids = {}
    for nome, descricao in segmentos_info.items():
        segmentos_ids[nome] = collector.criar_segmento(nome, descricao)
    
    # ================================================
    # COLETAR DADOS DE CADA ÍNDICE
    # ================================================
    total_indices = len(indices_para_coletar)
    
    for idx, indice_info in enumerate(indices_para_coletar, 1):
        logger.info(f"\n[{idx}/{total_indices}] Processando índice...")
        
        # Coletar dados do índice
        collector.coletar_indice_completo(
            ticker=indice_info['ticker'],
            descricao=indice_info['descricao'],
            pais=indice_info['pais'],
            periodo="2y"  # 2 anos de dados
        )
        
        # Associar ao segmento
        id_segmento = segmentos_ids.get(indice_info['segmento'])
        if id_segmento:
            collector.associar_indice_segmento(
                ticker=indice_info['ticker'],
                id_segmento=id_segmento
            )
        
        # Delay para não sobrecarregar a API
        if idx < total_indices:
            time.sleep(1)
    
    logger.info("\n" + "="*60)
    logger.info("✅ COLETA CONCLUÍDA COM SUCESSO!")
    logger.info("="*60 + "\n")

if __name__ == '__main__':
    executar_coleta_completa()