from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.database import db, User
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def token_required(f):
    """Decorator para verificar se o usuário está autenticado"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token de acesso é obrigatório'}), 401
        
        try:
            # Remove 'Bearer ' do token se presente
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, os.getenv('SECRET_KEY', 'fishing-app-secret-key-2024'), algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'error': 'Token inválido'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registra um novo usuário"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('email'):
            return jsonify({'error': 'Email é obrigatório'}), 400
        if not data.get('username'):
            return jsonify({'error': 'Username é obrigatório'}), 400
        if not data.get('password'):
            return jsonify({'error': 'Senha é obrigatória'}), 400
        
        # Verificar se usuário já existe
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email já está em uso'}), 400
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username já está em uso'}), 400
        
        # Criar novo usuário
        password_hash = generate_password_hash(data['password'])
        user = User(
            email=data['email'],
            username=data['username'],
            password_hash=password_hash
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Gerar token
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=30)
        }, os.getenv('SECRET_KEY', 'fishing-app-secret-key-2024'), algorithm='HS256')
        
        return jsonify({
            'message': 'Usuário criado com sucesso!',
            'user': user.to_dict(),
            'token': token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Faz login do usuário"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('email'):
            return jsonify({'error': 'Email é obrigatório'}), 400
        if not data.get('password'):
            return jsonify({'error': 'Senha é obrigatória'}), 400
        
        # Buscar usuário
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not check_password_hash(user.password_hash, data['password']):
            return jsonify({'error': 'Email ou senha incorretos'}), 401
        
        # Gerar token
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.utcnow() + timedelta(days=30)
        }, os.getenv('SECRET_KEY', 'fishing-app-secret-key-2024'), algorithm='HS256')
        
        return jsonify({
            'message': 'Login realizado com sucesso!',
            'user': user.to_dict(),
            'token': token
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Retorna informações do usuário atual"""
    return jsonify({
        'user': current_user.to_dict()
    }), 200

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """Altera a senha do usuário"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('current_password'):
            return jsonify({'error': 'Senha atual é obrigatória'}), 400
        if not data.get('new_password'):
            return jsonify({'error': 'Nova senha é obrigatória'}), 400
        
        # Verificar senha atual
        if not check_password_hash(current_user.password_hash, data['current_password']):
            return jsonify({'error': 'Senha atual incorreta'}), 401
        
        # Atualizar senha
        current_user.password_hash = generate_password_hash(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'message': 'Senha alterada com sucesso!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

