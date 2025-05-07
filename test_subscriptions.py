import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import text, Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Create test app with SQLite
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'test-secret-key'  # Only for testing

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Define models for testing
class BaseModel(db.Model):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class User(BaseModel):
    __tablename__ = 'users'
    
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    subscriptions = relationship('Subscription', back_populates='user')

class SubscriptionPlan(BaseModel):
    __tablename__ = 'subscription_plans'
    
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)
    description = Column(String)
    price = Column(Numeric(10, 2), nullable=False)
    duration_days = Column(Integer, nullable=False)
    features = Column(JSON)
    is_active = Column(Boolean, default=True)
    
    subscriptions = relationship('Subscription', back_populates='plan')
    
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

class Subscription(BaseModel):
    __tablename__ = 'subscriptions'
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default='active')
    auto_renew = Column(Boolean, default=True)
    
    user = relationship('User', back_populates='subscriptions')
    plan = relationship('SubscriptionPlan', back_populates='subscriptions')
    
    def is_active(self):
        now = datetime.now(timezone.utc)
        return self.status == 'active' and now <= self.end_date
    
    def cancel(self):
        self.status = 'cancelled'
        self.auto_renew = False
    
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

def create_test_data():
    """Create test data for performance testing"""
    print("Creating test plans...")
    # Create more test plans with different types
    plans = []
    plan_types = ['free', 'basic', 'pro']
    for i in range(1000):  
        plan_type = plan_types[i % len(plan_types)]
        plans.append(
            SubscriptionPlan(
                name=f"Test Plan {i}",
                type=plan_type,
                description=f"Test plan {i} description with more details about features and benefits",
                price=10.00 * (i + 1),
                duration_days=30 * (i % 3 + 1),  # 30, 60, or 90 days
                features={
                    "feature1": True,
                    "feature2": False,
                    "feature3": i % 2 == 0,
                    "feature4": i % 3 == 0,
                    "feature5": i % 4 == 0
                },
                is_active=i % 5 != 0  # Some plans are inactive
            )
        )
    db.session.add_all(plans)
    db.session.commit()

    print("Creating test users...")
    # Create more test users
    users = []
    for i in range(1000):  # Increased from 5 to 100 users
        users.append(
            User(
                email=f"test{i}@example.com",
                password_hash="dummy_hash",
                is_active=i % 10 != 0,  # Some users are inactive
                is_admin=(i < 5)  # First 5 users are admin
            )
        )
    db.session.add_all(users)
    db.session.commit()

    print("Creating test subscriptions...")
    # Create more test subscriptions with varied statuses
    subscriptions = []
    statuses = ['active', 'cancelled', 'expired', 'upgraded']
    for i, user in enumerate(users):
        # Each user gets 1-3 subscriptions
        num_subscriptions = (i % 3) + 1
        for j in range(num_subscriptions):
            plan = plans[i % len(plans)]
            start_date = datetime.now(timezone.utc) - timedelta(days=i*5)
            end_date = start_date + timedelta(days=plan.duration_days)
            status = statuses[i % len(statuses)]
            subscriptions.append(
                Subscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    auto_renew=(status == 'active' and i % 2 == 0)
                )
            )
    db.session.add_all(subscriptions)
    db.session.commit()
    print(f"Created {len(plans)} plans, {len(users)} users, and {len(subscriptions)} subscriptions")

def test_performance():
    """Compare performance between ORM and raw SQL queries"""
    print("\n=== Performance Tests ===")
    
    # Test 1: Get active subscriptions with plan details
    print("\nTest 1: Get active subscriptions with plan details")
    
    # ORM approach
    start_time = time.time()
    orm_result = Subscription.query.join(Subscription.plan).filter(
        Subscription.status == 'active',
        Subscription.end_date > datetime.now(timezone.utc)
    ).all()
    orm_time = time.time() - start_time
    print(f"ORM Time: {orm_time:.4f} seconds")
    print(f"ORM Results: {len(orm_result)} subscriptions")
    
    # Raw SQL approach
    start_time = time.time()
    sql = text("""
        SELECT s.*, p.name as plan_name, p.price as plan_price
        FROM subscriptions s
        JOIN subscription_plans p ON s.plan_id = p.id
        WHERE s.status = 'active'
        AND s.end_date > :now
    """)
    sql_result = db.session.execute(sql, {'now': datetime.now(timezone.utc)}).fetchall()
    sql_time = time.time() - start_time
    print(f"Raw SQL Time: {sql_time:.4f} seconds")
    print(f"Raw SQL Results: {len(sql_result)} subscriptions")
    
    # Test 2: Get subscription statistics
    print("\nTest 2: Get subscription statistics")
    
    # ORM approach
    start_time = time.time()
    orm_stats = db.session.query(
        Subscription.plan_id,
        db.func.count(Subscription.id).label('total'),
        db.func.sum(db.case((Subscription.status == 'active', 1), else_=0)).label('active')
    ).group_by(Subscription.plan_id).all()
    orm_time = time.time() - start_time
    print(f"ORM Time: {orm_time:.4f} seconds")
    print(f"ORM Stats: {len(orm_stats)} plan statistics")
    
    # Raw SQL approach
    start_time = time.time()
    sql = text("""
        SELECT 
            plan_id,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active
        FROM subscriptions
        GROUP BY plan_id
    """)
    sql_stats = db.session.execute(sql).fetchall()
    sql_time = time.time() - start_time
    print(f"Raw SQL Time: {sql_time:.4f} seconds")
    print(f"Raw SQL Stats: {len(sql_stats)} plan statistics")

    # Test 3: Complex query - Get user subscription history with plan details
    print("\nTest 3: Complex query - User subscription history")
    
    # ORM approach
    start_time = time.time()
    orm_history = db.session.query(
        User.email,
        SubscriptionPlan.name.label('plan_name'),
        SubscriptionPlan.type.label('plan_type'),
        Subscription.start_date,
        Subscription.end_date,
        Subscription.status
    ).join(
        Subscription, User.id == Subscription.user_id
    ).join(
        SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id
    ).filter(
        User.is_active == True
    ).order_by(
        User.email, Subscription.start_date.desc()
    ).all()
    orm_time = time.time() - start_time
    print(f"ORM Time: {orm_time:.4f} seconds")
    print(f"ORM Results: {len(orm_history)} subscription history records")
    
    # Raw SQL approach
    start_time = time.time()
    sql = text("""
        SELECT 
            u.email,
            p.name as plan_name,
            p.type as plan_type,
            s.start_date,
            s.end_date,
            s.status
        FROM users u
        JOIN subscriptions s ON u.id = s.user_id
        JOIN subscription_plans p ON s.plan_id = p.id
        WHERE u.is_active = 1
        ORDER BY u.email, s.start_date DESC
    """)
    sql_history = db.session.execute(sql).fetchall()
    sql_time = time.time() - start_time
    print(f"Raw SQL Time: {sql_time:.4f} seconds")
    print(f"Raw SQL Results: {len(sql_history)} subscription history records")

    # Test 4: Complex aggregation - Plan usage statistics
    print("\nTest 4: Complex aggregation - Plan usage statistics")
    
    # ORM approach
    start_time = time.time()
    orm_usage = db.session.query(
        SubscriptionPlan.type,
        db.func.count(Subscription.id).label('total_subscriptions'),
        db.func.count(db.case((Subscription.status == 'active', 1))).label('active_subscriptions'),
        db.func.avg(SubscriptionPlan.price).label('avg_price'),
        db.func.max(SubscriptionPlan.duration_days).label('max_duration')
    ).join(
        Subscription, SubscriptionPlan.id == Subscription.plan_id
    ).group_by(
        SubscriptionPlan.type
    ).all()
    orm_time = time.time() - start_time
    print(f"ORM Time: {orm_time:.4f} seconds")
    print(f"ORM Results: {len(orm_usage)} plan type statistics")
    
    # Raw SQL approach
    start_time = time.time()
    sql = text("""
        SELECT 
            p.type,
            COUNT(s.id) as total_subscriptions,
            SUM(CASE WHEN s.status = 'active' THEN 1 ELSE 0 END) as active_subscriptions,
            AVG(p.price) as avg_price,
            MAX(p.duration_days) as max_duration
        FROM subscription_plans p
        LEFT JOIN subscriptions s ON p.id = s.plan_id
        GROUP BY p.type
    """)
    sql_usage = db.session.execute(sql).fetchall()
    sql_time = time.time() - start_time
    print(f"Raw SQL Time: {sql_time:.4f} seconds")
    print(f"Raw SQL Results: {len(sql_usage)} plan type statistics")

def test_subscription_handling():
    """Test subscription handling functionality"""
    print("\n=== Subscription Handling Tests ===")
    
    # Test 1: Create new subscription
    print("\nTest 1: Create new subscription")
    user = User.query.filter_by(is_admin=False).first()
    plan = SubscriptionPlan.query.first()
    
    subscription = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(days=plan.duration_days),
        status='active',
        auto_renew=True
    )
    db.session.add(subscription)
    db.session.commit()
    print(f"Created subscription ID: {subscription.id}")
    
    # Test 2: Cancel subscription
    print("\nTest 2: Cancel subscription")
    subscription.cancel()
    db.session.commit()
    print(f"Subscription status after cancel: {subscription.status}")
    print(f"Auto-renew after cancel: {subscription.auto_renew}")
    
    # Test 3: Upgrade subscription
    print("\nTest 3: Upgrade subscription")
    new_plan = SubscriptionPlan.query.filter(SubscriptionPlan.id != plan.id).first()
    old_sub = Subscription.query.filter_by(user_id=user.id, status='active').first()
    
    if old_sub:
        old_sub.status = 'upgraded'
        old_sub.auto_renew = False
        
        new_sub = Subscription(
            user_id=user.id,
            plan_id=new_plan.id,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(days=new_plan.duration_days),
            status='active',
            auto_renew=True
        )
        db.session.add(new_sub)
        db.session.commit()
        print(f"Upgraded from plan {old_sub.plan_id} to {new_sub.plan_id}")

def main():
    """Main test runner"""
    with app.app_context():
        # Clean up existing data
        db.drop_all()
        db.create_all()
        
        # Create test data
        print("Creating test data...")
        create_test_data()
        
        # Run tests
        test_performance()
        test_subscription_handling()
        
        # Clean up
        db.session.remove()
        print("\nTests completed!")

if __name__ == '__main__':
    main() 