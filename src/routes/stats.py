from flask import Blueprint, request, jsonify
from src.models.database import db, User, Location, FishingSession, Catch
from src.routes.auth import token_required
from sqlalchemy import func, desc
from datetime import datetime, timedelta

stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/overview', methods=['GET'])
@token_required
def get_overview_stats(current_user):
    """Retorna estatísticas gerais do usuário"""
    try:
        # Contadores básicos
        total_sessions = FishingSession.query.filter_by(user_id=current_user.id).count()
        total_catches = db.session.query(Catch).join(FishingSession).filter(
            FishingSession.user_id == current_user.id
        ).count()
        total_locations = Location.query.filter_by(user_id=current_user.id).count()
        
        # Peixes soltos vs mantidos
        released_count = db.session.query(Catch).join(FishingSession).filter(
            FishingSession.user_id == current_user.id,
            Catch.released == True
        ).count()
        
        kept_count = total_catches - released_count
        
        # Peso total capturado
        total_weight = db.session.query(func.sum(Catch.weight_kg)).join(FishingSession).filter(
            FishingSession.user_id == current_user.id,
            Catch.weight_kg.isnot(None)
        ).scalar() or 0
        
        # Tempo total de pesca (em horas)
        total_minutes = db.session.query(func.sum(FishingSession.duration_minutes)).filter(
            FishingSession.user_id == current_user.id,
            FishingSession.duration_minutes.isnot(None)
        ).scalar() or 0
        
        total_hours = round(total_minutes / 60, 1) if total_minutes > 0 else 0
        
        # Última pescaria
        last_session = FishingSession.query.filter_by(user_id=current_user.id).order_by(
            desc(FishingSession.date), desc(FishingSession.start_time)
        ).first()
        
        return jsonify({
            'overview': {
                'total_sessions': total_sessions,
                'total_catches': total_catches,
                'total_locations': total_locations,
                'released_count': released_count,
                'kept_count': kept_count,
                'total_weight_kg': round(total_weight, 2),
                'total_hours': total_hours,
                'last_session_date': last_session.date.isoformat() if last_session else None,
                'last_session_location': last_session.location.name if last_session else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/species', methods=['GET'])
@token_required
def get_species_stats(current_user):
    """Retorna estatísticas por espécie"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Contagem por espécie
        species_counts = db.session.query(
            Catch.species,
            func.count(Catch.id).label('count'),
            func.avg(Catch.weight_kg).label('avg_weight'),
            func.sum(Catch.weight_kg).label('total_weight'),
            func.count(func.nullif(Catch.released, False)).label('released_count')
        ).join(FishingSession).filter(
            FishingSession.user_id == current_user.id
        ).group_by(Catch.species).order_by(desc('count')).limit(limit).all()
        
        species_data = []
        for species, count, avg_weight, total_weight, released_count in species_counts:
            species_data.append({
                'species': species,
                'count': count,
                'avg_weight_kg': round(avg_weight, 2) if avg_weight else None,
                'total_weight_kg': round(total_weight, 2) if total_weight else None,
                'released_count': released_count,
                'kept_count': count - released_count
            })
        
        return jsonify({
            'species_stats': species_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/locations', methods=['GET'])
@token_required
def get_location_stats(current_user):
    """Retorna estatísticas por local"""
    try:
        # Estatísticas por local
        location_stats = db.session.query(
            Location.id,
            Location.name,
            func.count(FishingSession.id).label('sessions_count'),
            func.count(Catch.id).label('catches_count'),
            func.sum(FishingSession.duration_minutes).label('total_minutes'),
            func.avg(Catch.weight_kg).label('avg_weight')
        ).outerjoin(FishingSession).outerjoin(Catch).filter(
            Location.user_id == current_user.id
        ).group_by(Location.id, Location.name).order_by(desc('sessions_count')).all()
        
        locations_data = []
        for location_id, name, sessions_count, catches_count, total_minutes, avg_weight in location_stats:
            total_hours = round(total_minutes / 60, 1) if total_minutes else 0
            locations_data.append({
                'location_id': location_id,
                'location_name': name,
                'sessions_count': sessions_count or 0,
                'catches_count': catches_count or 0,
                'total_hours': total_hours,
                'avg_weight_kg': round(avg_weight, 2) if avg_weight else None
            })
        
        return jsonify({
            'location_stats': locations_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/baits', methods=['GET'])
@token_required
def get_bait_stats(current_user):
    """Retorna estatísticas por isca"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Estatísticas por isca
        bait_stats = db.session.query(
            Catch.bait_used,
            func.count(Catch.id).label('count'),
            func.avg(Catch.weight_kg).label('avg_weight'),
            func.count(func.nullif(Catch.released, False)).label('released_count')
        ).join(FishingSession).filter(
            FishingSession.user_id == current_user.id,
            Catch.bait_used.isnot(None),
            Catch.bait_used != ''
        ).group_by(Catch.bait_used).order_by(desc('count')).limit(limit).all()
        
        baits_data = []
        for bait, count, avg_weight, released_count in bait_stats:
            baits_data.append({
                'bait': bait,
                'count': count,
                'avg_weight_kg': round(avg_weight, 2) if avg_weight else None,
                'released_count': released_count,
                'kept_count': count - released_count,
                'success_rate': round((count / total_catches * 100), 1) if total_catches > 0 else 0
            })
        
        # Calcular total de capturas para taxa de sucesso
        total_catches = db.session.query(Catch).join(FishingSession).filter(
            FishingSession.user_id == current_user.id
        ).count()
        
        # Recalcular taxa de sucesso
        for bait_data in baits_data:
            bait_data['success_rate'] = round((bait_data['count'] / total_catches * 100), 1) if total_catches > 0 else 0
        
        return jsonify({
            'bait_stats': baits_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/monthly', methods=['GET'])
@token_required
def get_monthly_stats(current_user):
    """Retorna estatísticas mensais dos últimos 12 meses"""
    try:
        # Calcular data de 12 meses atrás
        twelve_months_ago = datetime.now().date() - timedelta(days=365)
        
        # Estatísticas mensais de sessões
        monthly_sessions = db.session.query(
            func.date_trunc('month', FishingSession.date).label('month'),
            func.count(FishingSession.id).label('sessions_count'),
            func.sum(FishingSession.duration_minutes).label('total_minutes')
        ).filter(
            FishingSession.user_id == current_user.id,
            FishingSession.date >= twelve_months_ago
        ).group_by('month').order_by('month').all()
        
        # Estatísticas mensais de capturas
        monthly_catches = db.session.query(
            func.date_trunc('month', FishingSession.date).label('month'),
            func.count(Catch.id).label('catches_count'),
            func.sum(Catch.weight_kg).label('total_weight')
        ).join(FishingSession).filter(
            FishingSession.user_id == current_user.id,
            FishingSession.date >= twelve_months_ago
        ).group_by('month').order_by('month').all()
        
        # Combinar dados
        monthly_data = {}
        
        for month, sessions_count, total_minutes in monthly_sessions:
            month_str = month.strftime('%Y-%m')
            monthly_data[month_str] = {
                'month': month_str,
                'sessions_count': sessions_count,
                'total_hours': round(total_minutes / 60, 1) if total_minutes else 0,
                'catches_count': 0,
                'total_weight_kg': 0
            }
        
        for month, catches_count, total_weight in monthly_catches:
            month_str = month.strftime('%Y-%m')
            if month_str in monthly_data:
                monthly_data[month_str]['catches_count'] = catches_count
                monthly_data[month_str]['total_weight_kg'] = round(total_weight, 2) if total_weight else 0
        
        # Converter para lista ordenada
        monthly_list = list(monthly_data.values())
        monthly_list.sort(key=lambda x: x['month'])
        
        return jsonify({
            'monthly_stats': monthly_list
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@stats_bp.route('/recent', methods=['GET'])
@token_required
def get_recent_activity(current_user):
    """Retorna atividade recente do usuário"""
    try:
        limit = request.args.get('limit', 5, type=int)
        
        # Sessões recentes
        recent_sessions = FishingSession.query.filter_by(user_id=current_user.id).order_by(
            desc(FishingSession.date), desc(FishingSession.start_time)
        ).limit(limit).all()
        
        # Capturas recentes
        recent_catches = db.session.query(Catch).join(FishingSession).filter(
            FishingSession.user_id == current_user.id
        ).order_by(desc(Catch.created_at)).limit(limit).all()
        
        return jsonify({
            'recent_sessions': [session.to_dict() for session in recent_sessions],
            'recent_catches': [catch.to_dict() for catch in recent_catches]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

