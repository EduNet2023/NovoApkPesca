# 🎣 Fishing App API

Backend em Flask com integração ao Supabase e deploy no Render.

## 📦 Tecnologias

- Flask + Flask-CORS
- SQLAlchemy (SQLite ou Supabase)
- Blueprints modularizados
- Deploy automatizado via `render.yaml`

## 🚀 Executando localmente

```bash
# Crie o ambiente
python -m venv venv
source venv/bin/activate  # ou .\venv\Scripts\activate no Windows

# Instale as dependências
pip install -r requirements.txt

# Rode o app
python src/main.py
