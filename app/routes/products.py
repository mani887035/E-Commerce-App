from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.models import Product, Review, Favorite, SearchHistory
from app import db

products_bp = Blueprint('products', __name__)

CATEGORIES = ['electronics', 'fashion', 'home', 'beauty', 'books', 'sports', 'toys', 'grocery']


@products_bp.route('/')
def list_products():
    category = request.args.get('category')
    search = request.args.get('search')
    sort = request.args.get('sort', 'name')  # name, price_low, price_high, rating
    
    query = Product.query
    
    if category and category in CATEGORIES:
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.description.ilike(f'%{search}%')
            )
        )
        # Record search history if user is logged in
        if current_user.is_authenticated:
            search_record = SearchHistory(user_id=current_user.id, query=search)
            db.session.add(search_record)
            db.session.commit()
    
    # Sorting
    if sort == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort == 'rating':
        query = query.order_by(Product.avg_rating.desc())
    else:
        query = query.order_by(Product.name.asc())
    
    products = query.all()
    
    # Get user favorites if logged in
    user_favorites = []
    if current_user.is_authenticated:
        user_favorites = [f.product_id for f in current_user.favorites.all()]
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'success': True,
            'products': [p.to_dict() for p in products],
            'categories': CATEGORIES,
            'user_favorites': user_favorites
        })
    
    return render_template('products.html', 
                         products=products, 
                         categories=CATEGORIES,
                         current_category=category,
                         search_query=search,
                         user_favorites=user_favorites)


@products_bp.route('/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    reviews = product.reviews.order_by(Review.created_at.desc()).all()
    
    # Check if user has favorited this product
    is_favorite = False
    user_review = None
    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first() is not None
        user_review = Review.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'success': True,
            'product': product.to_dict(),
            'reviews': [r.to_dict() for r in reviews],
            'is_favorite': is_favorite,
            'user_review': user_review.to_dict() if user_review else None
        })
    
    return render_template('product_detail.html', 
                         product=product, 
                         reviews=reviews,
                         is_favorite=is_favorite,
                         user_review=user_review)


@products_bp.route('/<int:product_id>/review', methods=['POST'])
@login_required
def add_review(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.is_json:
        data = request.get_json()
        rating = data.get('rating')
        comment = data.get('comment', '')
    else:
        rating = request.form.get('rating', type=int)
        comment = request.form.get('comment', '')
    
    if not rating or rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Rating must be between 1 and 5'}), 400
    
    # Check if user already reviewed this product
    existing_review = Review.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.rating = rating
        existing_review.comment = comment
    else:
        # Create new review
        review = Review(
            user_id=current_user.id,
            product_id=product_id,
            rating=rating,
            comment=comment
        )
        db.session.add(review)
    
    db.session.commit()
    product.update_rating()
    
    return jsonify({
        'success': True, 
        'message': 'Review submitted successfully',
        'avg_rating': product.avg_rating,
        'rating_count': product.rating_count
    })


@products_bp.route('/<int:product_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(product_id):
    product = Product.query.get_or_404(product_id)
    
    existing = Favorite.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed', 'message': 'Removed from favorites'})
    else:
        favorite = Favorite(user_id=current_user.id, product_id=product_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added', 'message': 'Added to favorites'})


@products_bp.route('/favorites')
@login_required
def list_favorites():
    favorites = current_user.favorites.all()
    products = [f.product.to_dict() for f in favorites if f.product]
    
    if request.headers.get('Accept') == 'application/json':
        return jsonify({'success': True, 'favorites': products})
    
    return render_template('favorites.html', favorites=favorites)


@products_bp.route('/search-history')
@login_required
def search_history():
    history = current_user.search_history.order_by(SearchHistory.searched_at.desc()).limit(20).all()
    return jsonify({'success': True, 'history': [h.to_dict() for h in history]})


@products_bp.route('/categories')
def list_categories():
    return jsonify({'success': True, 'categories': CATEGORIES})
