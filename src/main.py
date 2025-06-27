import os
import sys
from dotenv import load_dotenv
from flask_cors import CORS

# Carrega as variáveis de ambiente
load_dotenv()

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from src.models.database import db
from src.routes.auth import auth_bp
from src.routes.locations import locations_bp
from src.routes.fishing_sessions import sessions_bp
from src.routes.catches import catches_bp
from src.routes.stats import stats_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# Configuração CORS para permitir requisições do frontend
CORS(app, origins=["http://localhost:3000", "http://localhost:5173", "*"])

# Configurações do Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fishing-app-secret-key-2024')

# Configuração do banco de dados
database_url = os.getenv('DATABASE_URL')
using_supabase = False

if database_url and not database_url.startswith('sqlite'):
    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }
        using_supabase = True
        print("🚀 Tentando conectar ao Supabase...")
    except Exception as e:
        print(f"⚠️ Erro na configuração do Supabase: {e}")
        using_supabase = False

# Fallback para SQLite se Supabase não estiver configurado
if not using_supabase:
    sqlite_path = os.path.join(os.path.dirname(__file__), 'database', 'app.db')
    os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_path}"
    print("📁 Usando SQLite local como banco de dados")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar banco de dados
db.init_app(app)

# Registrar blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(locations_bp, url_prefix='/api/locations')
app.register_blueprint(sessions_bp, url_prefix='/api/sessions')
app.register_blueprint(catches_bp, url_prefix='/api/catches')
app.register_blueprint(stats_bp, url_prefix='/api/stats')

# Criar tabelas
with app.app_context():
    try:
        db.create_all()
        if using_supabase:
            print("✅ Conectado ao Supabase com sucesso!")
        else:
            print("✅ Banco SQLite local criado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        # Se falhar com Supabase, tenta SQLite
        if using_supabase:
            print("🔄 Tentando fallback para SQLite...")
            sqlite_path = os.path.join(os.path.dirname(__file__), 'database', 'app.db')
            os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
            app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{sqlite_path}"
            using_supabase = False
            try:
                db.create_all()
                print("✅ Fallback para SQLite realizado com sucesso!")
            except Exception as e2:
                print(f"❌ Erro crítico: {e2}")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve o frontend React ou arquivos estáticos"""
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "Frontend não encontrado. Execute o build do React primeiro.", 404

@app.route('/api/health')
def health_check():
    """Endpoint para verificar se a API está funcionando"""
    return {
        'status': 'ok',
        'message': 'Fishing App API está funcionando!',
        'database': 'Supabase' if using_supabase else 'SQLite Local'
    }

if __name__ == '__main__':
    print("🎣 Iniciando Fishing App API")
    if using_supabase:
        print("🚀 Modo: Supabase (dados permanentes na nuvem)")
    else:
        print("📁 Modo: SQLite local (dados temporários)")
    print("📊 Acesse http://localhost:5000 para testar a aplicação")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


