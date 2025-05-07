from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.subscription_plan import SubscriptionPlan
from app.models.subscription import Subscription
from app.models.user import User
from sqlalchemy import text
from datetime import datetime, UTC, timedelta, timezone

subscriptions_bp = Blueprint('subscriptions', __name__)

# --- Subscription Plan Endpoints ---

@subscriptions_bp.route('/plans', methods=['GET'])
def list_plans():
    """List all active subscription plans"""
    plan_type = request.args.get('type')
    query = SubscriptionPlan.query.filter_by(is_active=True)
    if plan_type:
        query = query.filter_by(type=plan_type)
    plans = query.all()
    return jsonify([plan.to_dict() for plan in plans]), 200

@subscriptions_bp.route('/plans', methods=['POST'])
@jwt_required()
def create_plan():
    """Create a new subscription plan (admin only)"""
    current_user = User.query.get(get_jwt_identity())
    if not current_user.is_admin:
        return jsonify({'msg': 'Admin access required'}), 403
        
    data = request.get_json()
    required_fields = ['name', 'type', 'price', 'duration_days']
    if not all(field in data for field in required_fields):
        return jsonify({'msg': 'Missing required fields'}), 400
        
    if data['type'] not in ['free', 'basic', 'pro']:
        return jsonify({'msg': 'Invalid plan type'}), 400
        
    plan = SubscriptionPlan(
        name=data['name'],
        type=data['type'],
        description=data.get('description'),
        price=data['price'],
        duration_days=data['duration_days'],
        features=data.get('features', {}),
        is_active=data.get('is_active', True)
    )
    db.session.add(plan)
    db.session.commit()
    
    return jsonify(plan.to_dict()), 201

@subscriptions_bp.route('/plans/<int:plan_id>', methods=['GET'])
def get_plan(plan_id):
    """Get a specific subscription plan"""
    plan = SubscriptionPlan.query.get_or_404(plan_id)
    return jsonify(plan.to_dict()), 200

# --- User Subscription Endpoints ---

@subscriptions_bp.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe():
    data = request.get_json()
    if 'plan_id' not in data:
        return jsonify({'msg': 'Plan ID is required'}), 400

    user_id = get_jwt_identity()
    plan = SubscriptionPlan.query.get_or_404(data['plan_id'])

    # Check for existing active subscription to this plan
    existing = Subscription.query.filter_by(
        user_id=user_id,
        plan_id=plan.id,
        status='active'
    ).first()
    if existing:
        return jsonify({'msg': 'You already have an active subscription to this plan.'}), 400

    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=plan.duration_days)
    subscription = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        start_date=start_date,
        end_date=end_date,
        auto_renew=data.get('auto_renew', True)
    )

    db.session.add(subscription)
    db.session.commit()

    return jsonify(subscription.to_dict()), 201

@subscriptions_bp.route('/my-subscription', methods=['GET'])
@jwt_required()
def get_my_subscriptions():
    """Get all current user's active subscriptions"""
    user_id = get_jwt_identity()
    
    # Using raw SQL for optimization
    sql = text("""
        SELECT s.*, p.name as plan_name, p.price as plan_price
        FROM subscriptions s
        JOIN subscription_plans p ON s.plan_id = p.id
        WHERE s.user_id = :user_id
        AND s.status = 'active'
        AND s.end_date > :now
        ORDER BY s.start_date DESC
    """)
    
    result = db.session.execute(sql, {'user_id': user_id, 'now': datetime.now(UTC)})
    subscriptions = result.fetchall()
    
    if not subscriptions:
        return jsonify({'msg': 'No active subscriptions found'}), 404
    
    return jsonify([
        {
            'id': sub.id,
            'plan_name': sub.plan_name,
            'plan_price': float(sub.plan_price),
            'start_date': sub.start_date.isoformat(),
            'end_date': sub.end_date.isoformat(),
            'status': sub.status,
            'auto_renew': sub.auto_renew
        }
        for sub in subscriptions
    ]), 200

@subscriptions_bp.route('/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription():
    data = request.get_json()
    if 'subscription_id' not in data:
        return jsonify({'msg': 'subscription_id is required'}), 400

    user_id = get_jwt_identity()
    subscription = Subscription.query.filter_by(id=data['subscription_id'], user_id=user_id, status='active').first()
    if not subscription:
        return jsonify({'msg': 'No active subscription found'}), 404

    subscription.cancel()
    return jsonify({'msg': 'Subscription cancelled successfully'}), 200

@subscriptions_bp.route('/history', methods=['GET'])
@jwt_required()
def subscription_history():
    """Get user's subscription history"""
    user_id = get_jwt_identity()
    
    # Using raw SQL for optimization with pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page
    
    sql = text("""
        SELECT s.*, p.name as plan_name, p.price as plan_price
        FROM subscriptions s
        JOIN subscription_plans p ON s.plan_id = p.id
        WHERE s.user_id = :user_id
        ORDER BY s.start_date DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = db.session.execute(
        sql,
        {'user_id': user_id, 'limit': per_page, 'offset': offset}
    )
    
    subscriptions = [{
        'id': row.id,
        'plan_name': row.plan_name,
        'plan_price': float(row.plan_price),
        'start_date': row.start_date.isoformat(),
        'end_date': row.end_date.isoformat(),
        'status': row.status,
        'auto_renew': row.auto_renew
    } for row in result]
    
    # Get total count
    total = db.session.execute(
        text('SELECT COUNT(*) FROM subscriptions WHERE user_id = :user_id'),
        {'user_id': user_id}
    ).scalar()
    
    return jsonify({
        'subscriptions': subscriptions,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }), 200

@subscriptions_bp.route('/upgrade', methods=['POST'])
@jwt_required()
def upgrade_subscription():
    data = request.get_json()
    if 'subscription_id' not in data or 'new_plan_id' not in data:
        return jsonify({'msg': 'subscription_id and new_plan_id are required'}), 400

    user_id = get_jwt_identity()
    old_sub = Subscription.query.filter_by(id=data['subscription_id'], user_id=user_id, status='active').first()
    if not old_sub:
        return jsonify({'msg': 'Active subscription not found'}), 404

    new_plan = SubscriptionPlan.query.get_or_404(data['new_plan_id'])
    # Mark old as upgraded
    old_sub.status = 'upgraded'
    old_sub.auto_renew = False
    db.session.commit()

    # Create new subscription
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=new_plan.duration_days)
    new_sub = Subscription(
        user_id=user_id,
        plan_id=new_plan.id,
        start_date=start_date,
        end_date=end_date,
        status='active',
        auto_renew=True
    )
    db.session.add(new_sub)
    db.session.commit()

    return jsonify(new_sub.to_dict()), 201 