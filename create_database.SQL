-- =====================================================
-- SCRIPT DE CRIAÇÃO DO BANCO DE DADOS SQL SERVER
-- Sistema de Análise de Oportunidades de Investimento
-- =====================================================

-- 1. Criar banco de dados
CREATE DATABASE InvestmentOpportunities;
GO

USE InvestmentOpportunities;
GO

-- 2. Tabela de Índices de Mercado
CREATE TABLE [dbo].[Indices] (
    [IdIndice] INT IDENTITY(1,1) PRIMARY KEY,
    [Ticker] VARCHAR(20) NOT NULL UNIQUE,
    [Descricao] VARCHAR(100) NOT NULL,
    [Pais] VARCHAR(50) NOT NULL,
    [DataCriacao] DATETIME DEFAULT GETDATE(),
    [Ativo] BIT DEFAULT 1
);

-- 3. Tabela de Dados Históricos
CREATE TABLE [dbo].[HistoricoPrecos] (
    [IdHistorico] BIGINT IDENTITY(1,1) PRIMARY KEY,
    [IdIndice] INT NOT NULL,
    [DataQuotacao] DATE NOT NULL,
    [Abertura] DECIMAL(18,4),
    [Alta] DECIMAL(18,4),
    [Baixa] DECIMAL(18,4),
    [Fechamento] DECIMAL(18,4),
    [FechamentoAjustado] DECIMAL(18,4),
    [Volume] BIGINT,
    [DataInsercao] DATETIME DEFAULT GETDATE(),
    FOREIGN KEY ([IdIndice]) REFERENCES [dbo].[Indices]([IdIndice]) ON DELETE CASCADE,
    CONSTRAINT UQ_HistoricoPrecos UNIQUE ([IdIndice], [DataQuotacao])
);

-- 4. Tabela de Segmentos de Investimento
CREATE TABLE [dbo].[SegmentosInvestimento] (
    [IdSegmento] INT IDENTITY(1,1) PRIMARY KEY,
    [Nome] VARCHAR(100) NOT NULL UNIQUE,
    [Descricao] VARCHAR(500),
    [DataCriacao] DATETIME DEFAULT GETDATE(),
    [Ativo] BIT DEFAULT 1
);

-- 5. Tabela de Relação entre Índices e Segmentos
CREATE TABLE [dbo].[IndicesSegmentos] (
    [IdIndiceSegmento] INT IDENTITY(1,1) PRIMARY KEY,
    [IdIndice] INT NOT NULL,
    [IdSegmento] INT NOT NULL,
    [Peso] DECIMAL(5,2) DEFAULT 100.00, -- Peso percentual do índice no segmento
    [DataCriacao] DATETIME DEFAULT GETDATE(),
    FOREIGN KEY ([IdIndice]) REFERENCES [dbo].[Indices]([IdIndice]) ON DELETE CASCADE,
    FOREIGN KEY ([IdSegmento]) REFERENCES [dbo].[SegmentosInvestimento]([IdSegmento]) ON DELETE CASCADE,
    CONSTRAINT UQ_IndiceSegmento UNIQUE ([IdIndice], [IdSegmento])
);

-- 6. Tabela de Análises e Oportunidades
CREATE TABLE [dbo].[OportunidadesInvestimento] (
    [IdOportunidade] BIGINT IDENTITY(1,1) PRIMARY KEY,
    [IdSegmento] INT NOT NULL,
    [Titulo] VARCHAR(200) NOT NULL,
    [Descricao] NVARCHAR(MAX),
    [TipoOportunidade] VARCHAR(50), -- 'COMPRA', 'VENDA', 'HOLD'
    [DataAnalise] DATE NOT NULL,
    [PrecoPrevisto] DECIMAL(18,4),
    [PotencialRetorno] DECIMAL(5,2), -- Percentual
    [NivelRisco] VARCHAR(20), -- 'BAIXO', 'MEDIO', 'ALTO'
    [Confianca] DECIMAL(3,2), -- De 0.00 a 1.00
    [DataCriacao] DATETIME DEFAULT GETDATE(),
    [Ativo] BIT DEFAULT 1,
    FOREIGN KEY ([IdSegmento]) REFERENCES [dbo].[SegmentosInvestimento]([IdSegmento]) ON DELETE CASCADE
);

-- 7. Tabela de Métricas Calculadas
CREATE TABLE [dbo].[MetricasSegmento] (
    [IdMetrica] BIGINT IDENTITY(1,1) PRIMARY KEY,
    [IdSegmento] INT NOT NULL,
    [DataCalculo] DATE NOT NULL,
    [RetornoMedio] DECIMAL(10,4),
    [VolatilidadeMedia] DECIMAL(10,4),
    [MaximaAlta] DECIMAL(18,4),
    [MaximaBaixa] DECIMAL(18,4),
    [Volume30Dias] BIGINT,
    [DataCriacao] DATETIME DEFAULT GETDATE(),
    FOREIGN KEY ([IdSegmento]) REFERENCES [dbo].[SegmentosInvestimento]([IdSegmento]) ON DELETE CASCADE,
    CONSTRAINT UQ_MetricasSegmento UNIQUE ([IdSegmento], [DataCalculo])
);

-- 8. Criar Índices para melhor performance
CREATE INDEX IX_HistoricoPrecos_IdIndice ON [dbo].[HistoricoPrecos]([IdIndice]);
CREATE INDEX IX_HistoricoPrecos_DataQuotacao ON [dbo].[HistoricoPrecos]([DataQuotacao]);
CREATE INDEX IX_IndicesSegmentos_IdSegmento ON [dbo].[IndicesSegmentos]([IdSegmento]);
CREATE INDEX IX_OportunidadesInvestimento_IdSegmento ON [dbo].[OportunidadesInvestimento]([IdSegmento]);
CREATE INDEX IX_OportunidadesInvestimento_DataAnalise ON [dbo].[OportunidadesInvestimento]([DataAnalise]);
CREATE INDEX IX_MetricasSegmento_DataCalculo ON [dbo].[MetricasSegmento]([DataCalculo]);

-- 9. Inserir Segmentos Iniciais
INSERT INTO [dbo].[SegmentosInvestimento] (Nome, Descricao)
VALUES 
    ('Tecnologia', 'Empresas e índices do setor de tecnologia e software'),
    ('Energia', 'Setor energético incluindo petróleo, gás e renováveis'),
    ('Financeiro', 'Instituições financeiras, bancos e seguradoras'),
    ('Saúde', 'Farmacêutica, biotecnologia e serviços de saúde'),
    ('Consumo', 'Bens de consumo, varejo e e-commerce'),
    ('Imobiliário', 'Imobiliárias, REITs e construção'),
    ('Telecomunicações', 'Operadoras de telecomunicações e provedores de internet'),
    ('Commodities', 'Mineração, agricultura e recursos naturais');

-- 10. View para análise consolidada
CREATE VIEW vw_AnaliseSegmentos AS
SELECT 
    seg.IdSegmento,
    seg.Nome AS Segmento,
    COUNT(DISTINCT hs.IdIndice) AS TotalIndices,
    MIN(hp.DataQuotacao) AS DataMaisAntiga,
    MAX(hp.DataQuotacao) AS DataMaisRecente,
    COUNT(hp.IdHistorico) AS TotalRegistrosPreco,
    AVG(CAST(hp.Volume AS FLOAT)) AS VolumeMediano
FROM [dbo].[SegmentosInvestimento] seg
LEFT JOIN [dbo].[IndicesSegmentos] hs ON seg.IdSegmento = hs.IdSegmento
LEFT JOIN [dbo].[HistoricoPrecos] hp ON hs.IdIndice = hp.IdIndice
WHERE seg.Ativo = 1
GROUP BY seg.IdSegmento, seg.Nome;

PRINT '✅ Banco de dados criado com sucesso!'
PRINT 'Tabelas criadas: Indices, HistoricoPrecos, SegmentosInvestimento, IndicesSegmentos, OportunidadesInvestimento, MetricasSegmento'