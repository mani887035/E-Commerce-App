from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('products.list_products'))
    
    if request.method == 'POST':
        # Handle JSON API request
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            if request.is_json:
                return jsonify({'success': True, 'message': 'Login successful', 'user': user.to_dict()})
            return redirect(url_for('products.list_products'))
        
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('products.list_products'))
    
    if request.method == 'POST':
        # Handle JSON API request
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
            name = data.get('name')
        else:
            email = request.form.get('email')
            password = request.form.get('password')
            name = request.form.get('name')
        
        # Validation
        if not email or not password or not name:
            if request.is_json:
                return jsonify({'success': False, 'message': 'All fields are required'}), 400
            flash('All fields are required', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Registration successful', 'user': user.to_dict()})
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out successfully'})
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    return jsonify({'success': True, 'user': current_user.to_dict()})
