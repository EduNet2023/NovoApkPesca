from flask import Blueprint, request, jsonify
from src.models.database import db, Catch, FishingSession
from src.routes.auth import token_required

catches_bp = Blueprint('catches', __name__)

@catches_bp.route('/', methods=['GET'])
@token_required
def get_catches(current_user):
    """Lista todas as capturas do usuário"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        session_id = request.args.get('session_id')
        species = request.args.get('species')
        released = request.args.get('released', type=bool)
        
        # Buscar capturas através das sessões do usuário
        query = db.session.query(Catch).join(FishingSession).filter(
            FishingSession.user_id == current_user.id
        )
        
        if session_id:
            query = query.filter(Catch.session_id == session_id)
        if species:
            query = query.filter(Catch.species.ilike(f'%{species}%'))
        if released is not None:
            query = query.filter(Catch.released == released)
        
        # Ordenar por data de criação mais recente
        query = query.order_by(Catch.created_at.desc())
        
        catches = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'catches': [catch.to_dict() for catch in catches.items],
            'total': catches.total,
            'pages': catches.pages,
            'current_page': catches.page,
            'per_page': catches.per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@catches_bp.route('/', methods=['POST'])
@token_required
def create_catch(current_user):
    """Cria uma nova captura"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('session_id'):
            return jsonify({'error': 'ID da sessão é obrigatório'}), 400
        if not data.get('species'):
            return jsonify({'error': 'Espécie do peixe é obrigatória'}), 400
        
        # Verificar se a sessão pertence ao usuário
        session = FishingSession.query.filter_by(
            id=data['session_id'],
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'error': 'Sessão não encontrada'}), 404
        
        # Criar nova captura
        catch = Catch(
            session_id=data['session_id'],
            species=data['species'],
            weight_kg=float(data['weight_kg']) if data.get('weight_kg') else None,
            length_cm=float(data['length_cm']) if data.get('length_cm') else None,
            bait_used=data.get('bait_used'),
            released=bool(data.get('released', False)),
            photo_url=data.get('photo_url')
        )
        
        db.session.add(catch)
        db.session.commit()
        
        return jsonify({
            'message': 'Captura registrada com sucesso!',
            'catch': catch.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': f'Erro de validação: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@catches_bp.route('/<catch_id>', methods=['GET'])
@token_required
def get_catch(current_user, catch_id):
    """Busca uma captura específica"""
    try:
        catch = db.session.query(Catch).join(FishingSession).filter(
            Catch.id == catch_id,
            FishingSession.user_id == current_user.id
        ).first()
        
        if not catch:
            return jsonify({'error': 'Captura não encontrada'}), 404
        
        return jsonify({
            'catch': catch.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@catches_bp.route('/<catch_id>', methods=['PUT'])
@token_required
def update_catch(current_user, catch_id):
    """Atualiza uma captura"""
    try:
        catch = db.session.query(Catch).join(FishingSession).filter(
            Catch.id == catch_id,
            FishingSession.user_id == current_user.id
        ).first()
        
        if not catch:
            return jsonify({'error': 'Captura não encontrada'}), 404
        
        data = request.get_json()
        
        # Verificar se a nova sessão pertence ao usuário (se fornecida)
        if data.get('session_id') and data['session_id'] != catch.session_id:
            session = FishingSession.query.filter_by(
                id=data['session_id'],
                user_id=current_user.id
            ).first()
            
            if not session:
                return jsonify({'error': 'Sessão não encontrada'}), 404
        
        # Atualizar campos
        if 'session_id' in data:
            catch.session_id = data['session_id']
        if 'species' in data:
            catch.species = data['species']
        if 'weight_kg' in data:
            catch.weight_kg = float(data['weight_kg']) if data['weight_kg'] else None
        if 'length_cm' in data:
            catch.length_cm = float(data['length_cm']) if data['length_cm'] else None
        if 'bait_used' in data:
            catch.bait_used = data['bait_used']
        if 'released' in data:
            catch.released = bool(data['released'])
        if 'photo_url' in data:
            catch.photo_url = data['photo_url']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Captura atualizada com sucesso!',
            'catch': catch.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Erro de validação: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@catches_bp.route('/<catch_id>', methods=['DELETE'])
@token_required
def delete_catch(current_user, catch_id):
    """Exclui uma captura"""
    try:
        catch = db.session.query(Catch).join(FishingSession).filter(
            Catch.id == catch_id,
            FishingSession.user_id == current_user.id
        ).first()
        
        if not catch:
            return jsonify({'error': 'Captura não encontrada'}), 404
        
        species = catch.species
        weight = catch.weight_kg
        
        db.session.delete(catch)
        db.session.commit()
        
        weight_text = f" ({weight}kg)" if weight else ""
        return jsonify({
            'message': f'Captura de {species}{weight_text} excluída com sucesso!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@catches_bp.route('/session/<session_id>', methods=['GET'])
@token_required
def get_catches_by_session(current_user, session_id):
    """Lista todas as capturas de uma sessão específica"""
    try:
        # Verificar se a sessão pertence ao usuário
        session = FishingSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'error': 'Sessão não encontrada'}), 404
        
        catches = Catch.query.filter_by(session_id=session_id).order_by(Catch.created_at.desc()).all()
        
        return jsonify({
            'catches': [catch.to_dict() for catch in catches],
            'session_info': {
                'id': session.id,
                'date': session.date.isoformat(),
                'location_name': session.location.name
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

