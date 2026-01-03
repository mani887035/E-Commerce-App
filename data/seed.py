"""
Database Seeder Script
Run this to populate the database with sample products
Usage: python seed.py [--force]  # Use --force to replace all products
"""
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Product


def seed_products(force=False):
    """Seed the database with sample products from JSON file"""
    app = create_app()
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Load products from JSON
        data_path = os.path.join(os.path.dirname(__file__), 'products.json')
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except FileNotFoundError:
            print(f"Products file not found at {data_path}")
            return
        
        existing_count = Product.query.count()
        
        if existing_count > 0 and force:
            print(f"Deleting {existing_count} existing products...")
            Product.query.delete()
            db.session.commit()
            existing_count = 0
        
        if existing_count > 0:
            print(f"Database already has {existing_count} products. Use --force to replace.")
            return
        
        # Add new products to database
        for product_data in products_data:
            product = Product(
                name=product_data['name'],
                description=product_data['description'],
                price=product_data['price'],
                category=product_data['category'],
                image_url=product_data.get('image_url'),
                stock=product_data.get('stock', 100),
                avg_rating=product_data.get('avg_rating', 4.0),
                rating_count=product_data.get('rating_count', 0)
            )
            db.session.add(product)
        
        db.session.commit()
        print(f"Successfully seeded {len(products_data)} products!")
        
        # Print summary by category
        categories = ['electronics', 'fashion', 'home', 'beauty', 'books', 'sports', 'toys', 'grocery']
        for cat in categories:
            count = Product.query.filter_by(category=cat).count()
            if count > 0:
                print(f"  - {cat.title()}: {count} products")


if __name__ == '__main__':
    force = '--force' in sys.argv
    seed_products(force=force)

