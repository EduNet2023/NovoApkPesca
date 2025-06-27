from flask import Blueprint, request, jsonify
from src.models.database import db, Location
from src.routes.auth import token_required

locations_bp = Blueprint('locations', __name__)

@locations_bp.route('/', methods=['GET'])
@token_required
def get_locations(current_user):
    """Lista todos os locais de pesca do usuário"""
    try:
        locations = Location.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'locations': [location.to_dict() for location in locations]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@locations_bp.route('/', methods=['POST'])
@token_required
def create_location(current_user):
    """Cria um novo local de pesca"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('name'):
            return jsonify({'error': 'Nome do local é obrigatório'}), 400
        if not data.get('latitude'):
            return jsonify({'error': 'Latitude é obrigatória'}), 400
        if not data.get('longitude'):
            return jsonify({'error': 'Longitude é obrigatória'}), 400
        
        # Verificar se já existe um local com o mesmo nome para este usuário
        existing_location = Location.query.filter_by(
            user_id=current_user.id,
            name=data['name']
        ).first()
        
        if existing_location:
            return jsonify({'error': 'Já existe um local com este nome'}), 400
        
        # Criar novo local
        location = Location(
            user_id=current_user.id,
            name=data['name'],
            latitude=float(data['latitude']),
            longitude=float(data['longitude']),
            description=data.get('description')
        )
        
        db.session.add(location)
        db.session.commit()
        
        return jsonify({
            'message': 'Local criado com sucesso!',
            'location': location.to_dict()
        }), 201
        
    except ValueError:
        return jsonify({'error': 'Latitude e longitude devem ser números válidos'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@locations_bp.route('/<location_id>', methods=['GET'])
@token_required
def get_location(current_user, location_id):
    """Busca um local específico"""
    try:
        location = Location.query.filter_by(
            id=location_id,
            user_id=current_user.id
        ).first()
        
        if not location:
            return jsonify({'error': 'Local não encontrado'}), 404
        
        return jsonify({
            'location': location.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@locations_bp.route('/<location_id>', methods=['PUT'])
@token_required
def update_location(current_user, location_id):
    """Atualiza um local de pesca"""
    try:
        location = Location.query.filter_by(
            id=location_id,
            user_id=current_user.id
        ).first()
        
        if not location:
            return jsonify({'error': 'Local não encontrado'}), 404
        
        data = request.get_json()
        
        # Verificar se o novo nome já existe (exceto para o próprio local)
        if data.get('name') and data['name'] != location.name:
            existing_location = Location.query.filter_by(
                user_id=current_user.id,
                name=data['name']
            ).first()
            
            if existing_location:
                return jsonify({'error': 'Já existe um local com este nome'}), 400
        
        # Atualizar campos
        if 'name' in data:
            location.name = data['name']
        if 'latitude' in data:
            location.latitude = float(data['latitude'])
        if 'longitude' in data:
            location.longitude = float(data['longitude'])
        if 'description' in data:
            location.description = data['description']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Local atualizado com sucesso!',
            'location': location.to_dict()
        }), 200
        
    except ValueError:
        return jsonify({'error': 'Latitude e longitude devem ser números válidos'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@locations_bp.route('/<location_id>', methods=['DELETE'])
@token_required
def delete_location(current_user, location_id):
    """Exclui um local de pesca"""
    try:
        location = Location.query.filter_by(
            id=location_id,
            user_id=current_user.id
        ).first()
        
        if not location:
            return jsonify({'error': 'Local não encontrado'}), 404
        
        # Verificar se há sessões de pesca associadas a este local
        if location.fishing_sessions:
            return jsonify({
                'error': 'Não é possível excluir este local pois há sessões de pesca associadas a ele'
            }), 400
        
        location_name = location.name
        db.session.delete(location)
        db.session.commit()
        
        return jsonify({
            'message': f'Local "{location_name}" excluído com sucesso!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

