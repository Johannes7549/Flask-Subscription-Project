from app import db
from app.models.base import BaseModel
from sqlalchemy import Index

class SubscriptionPlan(BaseModel):
    __tablename__ = 'subscription_plans'
    
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False, index=True)  # 'free', 'basic', 'pro'
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    features = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    subscriptions = db.relationship('Subscription', back_populates='plan', lazy='dynamic')
    
    # Indexes for optimization
    __table_args__ = (
        Index('idx_plan_name', 'name'),
        Index('idx_plan_active', 'is_active'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'description': self.description,
            'price': float(self.price),
            'duration_days': self.duration_days,
            'features': self.features,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 