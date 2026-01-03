from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import Product, Order, OrderItem, ChatHistory
from app.services.rag_service import rag_service
from app import db

chatbot_bp = Blueprint('chatbot', __name__)


@chatbot_bp.route('/message', methods=['POST'])
@login_required
def chat_message():
    """Process a chat message from the user"""
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'success': False, 'message': 'Message cannot be empty'}), 400
    
    # Get user context (favorites, recent orders, etc.)
    context = {
        'user_name': current_user.name,
        'user_id': current_user.id
    }
    
    # Process message through RAG service
    response = rag_service.chat(current_user.id, message, context)
    
    # Save chat history
    chat_record = ChatHistory(
        user_id=current_user.id,
        message=message,
        response=response.get('response', '')
    )
    db.session.add(chat_record)
    db.session.commit()
    
    return jsonify(response)


@chatbot_bp.route('/order-verify', methods=['POST'])
@login_required
def verify_order():
    """Verify and confirm order through chatbot"""
    data = request.get_json()
    product_ids = data.get('product_ids', [])
    quantities = data.get('quantities', [])
    confirm = data.get('confirm', False)
    
    if not product_ids:
        return jsonify({
            'success': False,
            'message': 'No products specified for order'
        }), 400
    
    # Validate products
    products = []
    total = 0
    order_summary = []
    
    for i, product_id in enumerate(product_ids):
        product = Product.query.get(product_id)
        if not product:
            return jsonify({
                'success': False,
                'message': f'Product with ID {product_id} not found'
            }), 404
        
        qty = quantities[i] if i < len(quantities) else 1
        
        if qty > product.stock:
            return jsonify({
                'success': False,
                'message': f'Not enough stock for {product.name}. Available: {product.stock}'
            }), 400
        
        products.append({'product': product, 'quantity': qty})
        subtotal = product.price * qty
        total += subtotal
        order_summary.append({
            'name': product.name,
            'price': product.price,
            'quantity': qty,
            'subtotal': subtotal
        })
    
    if not confirm:
        # Return order summary for confirmation
        return jsonify({
            'success': True,
            'action': 'pending_confirmation',
            'message': f"Here's your order summary:\n\n" + 
                      "\n".join([f"• {item['name']} x{item['quantity']} = ${item['subtotal']:.2f}" for item in order_summary]) +
                      f"\n\nTotal: ${total:.2f}\n\nWould you like to confirm this order?",
            'order_summary': order_summary,
            'total': total,
            'product_ids': product_ids,
            'quantities': quantities
        })
    
    # Create the order
    order = Order(
        user_id=current_user.id,
        total_amount=total,
        status='pending'
    )
    db.session.add(order)
    db.session.flush()
    
    for item in products:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item['product'].id,
            quantity=item['quantity'],
            price=item['product'].price
        )
        db.session.add(order_item)
        item['product'].stock -= item['quantity']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'action': 'order_created',
        'message': f"🎉 Your order #{order.id} has been placed successfully!\n\n" +
                  f"Total: ${total:.2f}\n" +
                  f"Status: {order.status.title()}\n\n" +
                  "Thank you for shopping with us!",
        'order': order.to_dict()
    })


@chatbot_bp.route('/history')
@login_required
def chat_history():
    """Get chat history for current user"""
    history = ChatHistory.query.filter_by(user_id=current_user.id)\
        .order_by(ChatHistory.created_at.desc())\
        .limit(50)\
        .all()
    
    return jsonify({
        'success': True,
        'history': [h.to_dict() for h in reversed(history)]
    })


@chatbot_bp.route('/clear-history', methods=['POST'])
@login_required
def clear_chat_history():
    """Clear chat history for current user"""
    ChatHistory.query.filter_by(user_id=current_user.id).delete()
    rag_service.clear_memory(current_user.id)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Chat history cleared'
    })


@chatbot_bp.route('/init', methods=['POST'])
def initialize_rag():
    """Initialize RAG service with current products"""
    products = Product.query.all()
    product_data = [p.to_dict() for p in products]
    
    success = rag_service.initialize(product_data)
    
    return jsonify({
        'success': success,
        'message': 'RAG service initialized' if success else 'Failed to initialize RAG service'
    })
