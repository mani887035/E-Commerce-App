from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.models import Order, OrderItem, Product
from app import db

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/')
@login_required
def list_orders():
    orders = current_user.orders.order_by(Order.order_date.desc()).all()
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({'success': True, 'orders': [o.to_dict() for o in orders]})
    
    return render_template('orders.html', orders=orders)


@orders_bp.route('/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Ensure user can only view their own orders
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    return jsonify({'success': True, 'order': order.to_dict()})


@orders_bp.route('/create', methods=['POST'])
@login_required
def create_order():
    data = request.get_json()
    
    items = data.get('items', [])  # List of {product_id, quantity}
    shipping_address = data.get('shipping_address', '')
    
    if not items:
        return jsonify({'success': False, 'message': 'Order must contain at least one item'}), 400
    
    # Validate products and calculate total
    total_amount = 0
    order_items = []
    
    for item in items:
        product = Product.query.get(item.get('product_id'))
        if not product:
            return jsonify({'success': False, 'message': f'Product not found: {item.get("product_id")}'}), 400
        
        quantity = item.get('quantity', 1)
        if quantity < 1:
            return jsonify({'success': False, 'message': 'Quantity must be at least 1'}), 400
        
        if quantity > product.stock:
            return jsonify({'success': False, 'message': f'Not enough stock for {product.name}'}), 400
        
        subtotal = product.price * quantity
        total_amount += subtotal
        
        order_items.append({
            'product': product,
            'quantity': quantity,
            'price': product.price
        })
    
    # Create order
    order = Order(
        user_id=current_user.id,
        total_amount=total_amount,
        shipping_address=shipping_address,
        status='pending'
    )
    db.session.add(order)
    db.session.flush()  # Get order ID
    
    # Create order items and update stock
    for item_data in order_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data['product'].id,
            quantity=item_data['quantity'],
            price=item_data['price']
        )
        db.session.add(order_item)
        
        # Update stock
        item_data['product'].stock -= item_data['quantity']
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': 'Order created successfully',
        'order': order.to_dict()
    })


@orders_bp.route('/<int:order_id>/confirm', methods=['POST'])
@login_required
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if order.status != 'pending':
        return jsonify({'success': False, 'message': 'Order cannot be confirmed'}), 400
    
    order.status = 'confirmed'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Order confirmed successfully',
        'order': order.to_dict()
    })


@orders_bp.route('/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    if order.status not in ['pending', 'confirmed']:
        return jsonify({'success': False, 'message': 'Order cannot be cancelled'}), 400
    
    # Restore stock
    for item in order.items:
        item.product.stock += item.quantity
    
    order.status = 'cancelled'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Order cancelled successfully',
        'order': order.to_dict()
    })


@orders_bp.route('/pending')
@login_required
def pending_orders():
    """Get pending orders for chatbot verification"""
    orders = current_user.orders.filter_by(status='pending').all()
    return jsonify({
        'success': True,
        'orders': [o.to_dict() for o in orders]
    })
