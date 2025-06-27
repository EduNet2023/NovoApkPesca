from flask import Blueprint, request, jsonify
from src.models.database import db, FishingSession, Location
from src.routes.auth import token_required
from datetime import datetime, timedelta

sessions_bp = Blueprint('sessions', __name__)

@sessions_bp.route('/', methods=['GET'])
@token_required
def get_sessions(current_user):
    """Lista todas as sessões de pesca do usuário"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        location_id = request.args.get('location_id')
        
        query = FishingSession.query.filter_by(user_id=current_user.id)
        
        if location_id:
            query = query.filter_by(location_id=location_id)
        
        # Ordenar por data mais recente
        query = query.order_by(FishingSession.date.desc(), FishingSession.start_time.desc())
        
        sessions = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'sessions': [session.to_dict() for session in sessions.items],
            'total': sessions.total,
            'pages': sessions.pages,
            'current_page': sessions.page,
            'per_page': sessions.per_page
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sessions_bp.route('/', methods=['POST'])
@token_required
def create_session(current_user):
    """Cria uma nova sessão de pesca"""
    try:
        data = request.get_json()
        
        # Validações
        if not data.get('location_id'):
            return jsonify({'error': 'Local é obrigatório'}), 400
        if not data.get('date'):
            return jsonify({'error': 'Data é obrigatória'}), 400
        if not data.get('start_time'):
            return jsonify({'error': 'Hora de início é obrigatória'}), 400
        if not data.get('end_time'):
            return jsonify({'error': 'Hora de término é obrigatória'}), 400
        
        # Verificar se o local pertence ao usuário
        location = Location.query.filter_by(
            id=data['location_id'],
            user_id=current_user.id
        ).first()
        
        if not location:
            return jsonify({'error': 'Local não encontrado'}), 404
        
        # Converter strings para objetos datetime
        try:
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        except ValueError:
            return jsonify({'error': 'Formato de data/hora inválido. Use YYYY-MM-DD para data e HH:MM para hora'}), 400
        
        # Calcular duração
        start_datetime = datetime.combine(date, start_time)
        end_datetime = datetime.combine(date, end_time)
        
        # Se end_time for menor que start_time, assume que terminou no dia seguinte
        if end_datetime < start_datetime:
            end_datetime = datetime.combine(date + timedelta(days=1), end_time)
        
        duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        
        # Criar nova sessão
        session = FishingSession(
            user_id=current_user.id,
            location_id=data['location_id'],
            date=date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            weather_conditions=data.get('weather_conditions'),
            temperature_celsius=float(data['temperature_celsius']) if data.get('temperature_celsius') else None,
            notes=data.get('notes')
        )
        
        db.session.add(session)
        db.session.commit()
        
        return jsonify({
            'message': 'Sessão de pesca criada com sucesso!',
            'session': session.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': f'Erro de validação: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@sessions_bp.route('/<session_id>', methods=['GET'])
@token_required
def get_session(current_user, session_id):
    """Busca uma sessão específica com suas capturas"""
    try:
        session = FishingSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'error': 'Sessão não encontrada'}), 404
        
        session_data = session.to_dict()
        session_data['catches'] = [catch.to_dict() for catch in session.catches]
        
        return jsonify({
            'session': session_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sessions_bp.route('/<session_id>', methods=['PUT'])
@token_required
def update_session(current_user, session_id):
    """Atualiza uma sessão de pesca"""
    try:
        session = FishingSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'error': 'Sessão não encontrada'}), 404
        
        data = request.get_json()
        
        # Verificar se o novo local pertence ao usuário (se fornecido)
        if data.get('location_id') and data['location_id'] != session.location_id:
            location = Location.query.filter_by(
                id=data['location_id'],
                user_id=current_user.id
            ).first()
            
            if not location:
                return jsonify({'error': 'Local não encontrado'}), 404
        
        # Atualizar campos
        if 'location_id' in data:
            session.location_id = data['location_id']
        if 'date' in data:
            session.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        if 'start_time' in data:
            session.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        if 'end_time' in data:
            session.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        if 'weather_conditions' in data:
            session.weather_conditions = data['weather_conditions']
        if 'temperature_celsius' in data:
            session.temperature_celsius = float(data['temperature_celsius']) if data['temperature_celsius'] else None
        if 'notes' in data:
            session.notes = data['notes']
        
        # Recalcular duração se data/hora foram alteradas
        if any(field in data for field in ['date', 'start_time', 'end_time']):
            start_datetime = datetime.combine(session.date, session.start_time)
            end_datetime = datetime.combine(session.date, session.end_time)
            
            if end_datetime < start_datetime:
                end_datetime = datetime.combine(session.date + timedelta(days=1), session.end_time)
            
            session.duration_minutes = int((end_datetime - start_datetime).total_seconds() / 60)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Sessão atualizada com sucesso!',
            'session': session.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Erro de validação: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@sessions_bp.route('/<session_id>', methods=['DELETE'])
@token_required
def delete_session(current_user, session_id):
    """Exclui uma sessão de pesca"""
    try:
        session = FishingSession.query.filter_by(
            id=session_id,
            user_id=current_user.id
        ).first()
        
        if not session:
            return jsonify({'error': 'Sessão não encontrada'}), 404
        
        session_date = session.date.strftime('%d/%m/%Y')
        location_name = session.location.name
        
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({
            'message': f'Sessão de pesca do dia {session_date} em {location_name} excluída com sucesso!'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

