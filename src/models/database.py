from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_uuid():
    """Gera um UUID único para usar como chave primária"""
    return str(uuid.uuid4())

class User(db.Model):
    """Modelo para usuários do aplicativo"""
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    locations = db.relationship('Location', backref='user', lazy=True, cascade='all, delete-orphan')
    fishing_sessions = db.relationship('FishingSession', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Location(db.Model):
    """Modelo para locais de pesca"""
    __tablename__ = 'locations'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    fishing_sessions = db.relationship('FishingSession', backref='location', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Location {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class FishingSession(db.Model):
    """Modelo para sessões de pesca"""
    __tablename__ = 'fishing_sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    location_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=True)
    weather_conditions = db.Column(db.String(100), nullable=True)
    temperature_celsius = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    catches = db.relationship('Catch', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FishingSession {self.date} at {self.location.name}>'
    
    def calculate_duration(self):
        """Calcula a duração da sessão em minutos"""
        if self.start_time and self.end_time:
            start_datetime = datetime.combine(self.date, self.start_time)
            end_datetime = datetime.combine(self.date, self.end_time)
            
            # Se end_time for menor que start_time, assume que terminou no dia seguinte
            if end_datetime < start_datetime:
                end_datetime = datetime.combine(self.date + timedelta(days=1), self.end_time)
            
            duration = end_datetime - start_datetime
            return int(duration.total_seconds() / 60)
        return None
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else None,
            'date': self.date.isoformat(),
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_minutes': self.duration_minutes,
            'weather_conditions': self.weather_conditions,
            'temperature_celsius': self.temperature_celsius,
            'notes': self.notes,
            'catches_count': len(self.catches),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Catch(db.Model):
    """Modelo para peixes capturados"""
    __tablename__ = 'catches'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    session_id = db.Column(db.String(36), db.ForeignKey('fishing_sessions.id'), nullable=False)
    species = db.Column(db.String(100), nullable=False)
    weight_kg = db.Column(db.Float, nullable=True)
    length_cm = db.Column(db.Float, nullable=True)
    bait_used = db.Column(db.String(100), nullable=True)
    released = db.Column(db.Boolean, default=False, nullable=False)
    photo_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Catch {self.species} - {self.weight_kg}kg>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'species': self.species,
            'weight_kg': self.weight_kg,
            'length_cm': self.length_cm,
            'bait_used': self.bait_used,
            'released': self.released,
            'photo_url': self.photo_url,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

