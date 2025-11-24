from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func, desc
import pandas as pd
from datetime import datetime, timedelta
import logging
from functools import wraps

# =====================================================
# CONFIGURAÇÃO INICIAL
# =====================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'

# Configuração do banco de dados SQL Server
app.config['SQLALCHEMY_DATABASE_URI'] = (
    "mssql+pyodbc://@CAIO\\SQLEXPRESS/InvestmentOpportunities?"
    "driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 30}
}

db = SQLAlchemy(app)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# MODELOS DE DADOS (ORM)
# =====================================================
class Indices(db.Model):
    __tablename__ = 'Indices'
    
    IdIndice = db.Column(db.Integer, primary_key=True)
    Ticker = db.Column(db.String(20), unique=True, nullable=False)
    Descricao = db.Column(db.String(100), nullable=False)
    Pais = db.Column(db.String(50), nullable=False)
    DataCriacao = db.Column(db.DateTime, default=datetime.now)
    Ativo = db.Column(db.Boolean, default=True)

class HistoricoPrecos(db.Model):
    __tablename__ = 'HistoricoPrecos'
    
    IdHistorico = db.Column(db.BigInteger, primary_key=True)
    IdIndice = db.Column(db.Integer, db.ForeignKey('Indices.IdIndice'), nullable=False)
    DataQuotacao = db.Column(db.Date, nullable=False)
    Abertura = db.Column(db.Numeric(18,4))
    Alta = db.Column(db.Numeric(18,4))
    Baixa = db.Column(db.Numeric(18,4))
    Fechamento = db.Column(db.Numeric(18,4))
    FechamentoAjustado = db.Column(db.Numeric(18,4))
    Volume = db.Column(db.BigInteger)
    DataInsercao = db.Column(db.DateTime, default=datetime.now)
    
    indice = db.relationship('Indices', backref='historico_precos')

class SegmentosInvestimento(db.Model):
    __tablename__ = 'SegmentosInvestimento'
    
    IdSegmento = db.Column(db.Integer, primary_key=True)
    Nome = db.Column(db.String(100), unique=True, nullable=False)
    Descricao = db.Column(db.String(500))
    DataCriacao = db.Column(db.DateTime, default=datetime.now)
    Ativo = db.Column(db.Boolean, default=True)

class IndicesSegmentos(db.Model):
    __tablename__ = 'IndicesSegmentos'
    
    IdIndiceSegmento = db.Column(db.Integer, primary_key=True)
    IdIndice = db.Column(db.Integer, db.ForeignKey('Indices.IdIndice'), nullable=False)
    IdSegmento = db.Column(db.Integer, db.ForeignKey('SegmentosInvestimento.IdSegmento'), nullable=False)
    Peso = db.Column(db.Numeric(5,2), default=100.00)
    DataCriacao = db.Column(db.DateTime, default=datetime.now)

class OportunidadesInvestimento(db.Model):
    __tablename__ = 'OportunidadesInvestimento'
    
    IdOportunidade = db.Column(db.BigInteger, primary_key=True)
    IdSegmento = db.Column(db.Integer, db.ForeignKey('SegmentosInvestimento.IdSegmento'), nullable=False)
    Titulo = db.Column(db.String(200), nullable=False)
    Descricao = db.Column(db.String)
    TipoOportunidade = db.Column(db.String(50))
    DataAnalise = db.Column(db.Date, nullable=False)
    PrecoPrevisto = db.Column(db.Numeric(18,4))
    PotencialRetorno = db.Column(db.Numeric(5,2))
    NivelRisco = db.Column(db.String(20))
    Confianca = db.Column(db.Numeric(3,2))
    DataCriacao = db.Column(db.DateTime, default=datetime.now)
    Ativo = db.Column(db.Boolean, default=True)

# =====================================================
# SERVIÇOS DE ANÁLISE
# =====================================================
class AnalisadorInvestimentos:
    """Classe para análises de investimento"""
    
    @staticmethod
    def obter_dados_segmento(id_segmento, dias=365):
        """Obtém dados históricos de um segmento nos últimos N dias"""
        data_inicio = datetime.now() - timedelta(days=dias)
        
        query = db.session.execute(text('''
            SELECT 
                i.Ticker,
                i.Descricao,
                hp.DataQuotacao,
                hp.Fechamento,
                hp.FechamentoAjustado,
                hp.Volume,
                hp.Alta,
                hp.Baixa
            FROM HistoricoPrecos hp
            INNER JOIN Indices i ON hp.IdIndice = i.IdIndice
            INNER JOIN IndicesSegmentos seg ON i.IdIndice = seg.IdIndice
            WHERE seg.IdSegmento = :id_segmento
            AND hp.DataQuotacao >= :data_inicio
            ORDER BY i.Ticker, hp.DataQuotacao
        '''), {'id_segmento': id_segmento, 'data_inicio': data_inicio})
        
        return query.fetchall()
    
    @staticmethod
    def calcular_metricas_segmento(id_segmento):
        """Calcula métricas do segmento"""
        dados = AnalisadorInvestimentos.obter_dados_segmento(id_segmento, dias=365)
        
        if not dados:
            return None
        
        df = pd.DataFrame([
            {
                'Ticker': row[0],
                'DataQuotacao': row[2],
                'Fechamento': float(row[3]) if row[3] else 0,
                'Volume': row[5]
            }
            for row in dados
        ])
        
        if df.empty:
            return None
        
        # Calcular retornos
        df['Retorno'] = df.groupby('Ticker')['Fechamento'].pct_change() * 100
        
        metricas = {
            'RetornoMedio': df['Retorno'].mean(),
            'VolatilidadeMedia': df['Retorno'].std(),
            'PrecoMaximo': df['Fechamento'].max(),
            'PrecoMinimo': df['Fechamento'].min(),
            'VolumeTotal': df['Volume'].sum()
        }
        
        return metricas
    
    @staticmethod
    def gerar_oportunidades(id_segmento):
        """Gera oportunidades de investimento baseado em análise"""
        metricas = AnalisadorInvestimentos.calcular_metricas_segmento(id_segmento)
        
        if not metricas:
            return []
        
        oportunidades = []
        
        # Análise simplista de oportunidades
        retorno_medio = metricas['RetornoMedio']
        volatilidade = metricas['VolatilidadeMedia']
        
        # Determine tipo de oportunidade baseado em volatilidade e retorno
        if retorno_medio > 2:
            tipo = 'COMPRA'
            potencial = retorno_medio * 1.5
        elif retorno_medio < -1:
            tipo = 'VENDA'
            potencial = abs(retorno_medio) * 0.8
        else:
            tipo = 'HOLD'
            potencial = retorno_medio
        
        # Nível de risco baseado em volatilidade
        if volatilidade < 2:
            risco = 'BAIXO'
            confianca = 0.85
        elif volatilidade < 5:
            risco = 'MEDIO'
            confianca = 0.70
        else:
            risco = 'ALTO'
            confianca = 0.55
        
        oportunidade = {
            'id_segmento': id_segmento,
            'titulo': f'Oportunidade em Segmento',
            'descricao': f'Análise baseada em {365} dias de dados históricos',
            'tipo': tipo,
            'potencial_retorno': float(potencial),
            'nivel_risco': risco,
            'confianca': float(confianca),
            'metricas': metricas
        }
        
        oportunidades.append(oportunidade)
        return oportunidades

# =====================================================
# ROTAS DA APLICAÇÃO
# =====================================================
@app.route('/')
def index():
    """Página inicial com lista de segmentos"""
    try:
        segmentos = db.session.query(SegmentosInvestimento).filter_by(Ativo=True).all()
        return render_template('index.html', segmentos=segmentos)
    except Exception as e:
        logger.error(f"Erro ao carregar página inicial: {e}")
        return render_template('error.html', erro=str(e)), 500

@app.route('/api/segmentos')
def api_segmentos():
    """API: Lista todos os segmentos"""
    try:
        segmentos = db.session.query(SegmentosInvestimento).filter_by(Ativo=True).all()
        return jsonify([{
            'id': seg.IdSegmento,
            'nome': seg.Nome,
            'descricao': seg.Descricao,
            'total_indices': len(db.session.query(IndicesSegmentos)
                                .filter_by(IdSegmento=seg.IdSegmento).all())
        } for seg in segmentos])
    except Exception as e:
        logger.error(f"Erro ao buscar segmentos: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/segmento/<int:id_segmento>')
def detalhes_segmento(id_segmento):
    """Página de detalhes de um segmento"""
    try:
        segmento = db.session.query(SegmentosInvestimento).get(id_segmento)
        if not segmento:
            return render_template('error.html', erro='Segmento não encontrado'), 404
        
        indices = db.session.execute(text('''
            SELECT i.IdIndice, i.Ticker, i.Descricao, COUNT(hp.IdHistorico) as TotalRegistros
            FROM Indices i
            LEFT JOIN HistoricoPrecos hp ON i.IdIndice = hp.IdIndice
            INNER JOIN IndicesSegmentos seg ON i.IdIndice = seg.IdIndice
            WHERE seg.IdSegmento = :id_segmento
            GROUP BY i.IdIndice, i.Ticker, i.Descricao
        '''), {'id_segmento': id_segmento}).fetchall()
        
        metricas = AnalisadorInvestimentos.calcular_metricas_segmento(id_segmento)
        oportunidades = AnalisadorInvestimentos.gerar_oportunidades(id_segmento)
        
        return render_template('detalhes_segmento.html',
                             segmento=segmento,
                             indices=indices,
                             metricas=metricas,
                             oportunidades=oportunidades)
    except Exception as e:
        logger.error(f"Erro ao carregar detalhes do segmento: {e}")
        return render_template('error.html', erro=str(e)), 500

@app.route('/api/segmento/<int:id_segmento>/grafico')
def api_grafico_segmento(id_segmento):
    """API: Retorna dados para gráfico de um segmento"""
    try:
        dias = request.args.get('dias', 90, type=int)
        dados = AnalisadorInvestimentos.obter_dados_segmento(id_segmento, dias=dias)
        
        # Agrupar por ticker
        dados_agrupados = {}
        for row in dados:
            ticker = row[0]
            if ticker not in dados_agrupados:
                dados_agrupados[ticker] = {'datas': [], 'precos': []}
            
            dados_agrupados[ticker]['datas'].append(str(row[2]))
            dados_agrupados[ticker]['precos'].append(float(row[3]) if row[3] else 0)
        
        return jsonify(dados_agrupados)
    except Exception as e:
        logger.error(f"Erro ao gerar gráfico: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/api/oportunidades')
def api_oportunidades():
    """API: Lista oportunidades de investimento"""
    try:
        id_segmento = request.args.get('segmento', type=int)
        
        query = db.session.query(OportunidadesInvestimento).filter_by(Ativo=True)
        
        if id_segmento:
            query = query.filter_by(IdSegmento=id_segmento)
        
        oportunidades = query.order_by(desc(OportunidadesInvestimento.DataAnalise)).all()
        
        return jsonify([{
            'id': opp.IdOportunidade,
            'titulo': opp.Titulo,
            'descricao': opp.Descricao,
            'tipo': opp.TipoOportunidade,
            'potencial_retorno': float(opp.PotencialRetorno) if opp.PotencialRetorno else 0,
            'nivel_risco': opp.NivelRisco,
            'confianca': float(opp.Confianca) if opp.Confianca else 0
        } for opp in oportunidades])
    except Exception as e:
        logger.error(f"Erro ao buscar oportunidades: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/dashboard')
def dashboard():
    """Dashboard com visão geral de todos os segmentos"""
    try:
        segmentos = db.session.query(SegmentosInvestimento).filter_by(Ativo=True).all()
        
        dashboard_data = []
        for seg in segmentos:
            metricas = AnalisadorInvestimentos.calcular_metricas_segmento(seg.IdSegmento)
            if metricas:
                dashboard_data.append({
                    'segmento': seg.Nome,
                    'metricas': metricas
                })
        
        return render_template('dashboard.html', dados=dashboard_data)
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}")
        return render_template('error.html', erro=str(e)), 500

@app.errorhandler(404)
def nao_encontrado(error):
    """Tratamento de erro 404"""
    return render_template('error.html', erro='Página não encontrada'), 404

@app.errorhandler(500)
def erro_interno(error):
    """Tratamento de erro 500"""
    return render_template('error.html', erro='Erro interno do servidor'), 500

# =====================================================
# INICIALIZAÇÃO
# =====================================================
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            logger.info("✓ Banco de dados conectado com sucesso")
        except Exception as e:
            logger.warning(f"⚠ Tabelas podem já existir: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)