from app import db
from app.models.base import BaseModel
from sqlalchemy import Index
from datetime import datetime, timedelta, timezone

class Subscription(BaseModel):
    __tablename__ = 'subscriptions'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')  # active, cancelled, expired
    auto_renew = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', back_populates='subscriptions')
    plan = db.relationship('SubscriptionPlan', back_populates='subscriptions')
    
    # Indexes for optimization
    __table_args__ = (
        Index('idx_sub_user_id', 'user_id'),
        Index('idx_sub_plan_id', 'plan_id'),
        Index('idx_sub_status', 'status'),
        Index('idx_sub_dates', 'start_date', 'end_date'),
    )
    
    def __init__(self, **kwargs):
        super(Subscription, self).__init__(**kwargs)
        if not self.end_date and self.plan:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
    
    from datetime import datetime, timezone

    def is_active(self):
        now = datetime.now(timezone.utc)
        end = self.end_date
        # If end_date is naive, make it aware (assume UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return self.status == 'active' and now <= end
    
    def cancel(self):
        self.status = 'cancelled'
        self.auto_renew = False
        self.save()
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_id': self.plan_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'status': self.status,
            'auto_renew': self.auto_renew,
            'is_active': self.is_active(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 