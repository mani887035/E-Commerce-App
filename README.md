# ShopSmart - E-Commerce Application

A full-stack e-commerce web application with AI-powered chatbot using LangChain RAG.

## Features

- 🛒 **Product Catalog**: Browse products in 5 categories (Toys, Electronics, Dresses, Cosmetics, Footwear)
- 🔐 **User Authentication**: Secure login and registration system
- ⭐ **Ratings & Reviews**: Leave reviews and ratings for products
- ❤️ **Favorites**: Save products for later
- 📦 **Order Management**: Place and track orders
- 🤖 **AI Chatbot**: LangChain RAG-powered assistant for product recommendations and order placement
- 📊 **Dashboard**: View order history, favorites, and search trends

## Tech Stack

- **Backend**: Flask + SQLAlchemy
- **Database**: SQLite
- **AI/RAG**: LangChain + OpenAI + FAISS
- **Frontend**: HTML/CSS/JavaScript

## Quick Start

### 1. Install Dependencies

```bash
cd c:\Users\manikandan\OneDrive\Documents\ecommerce
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Seed Database

```bash
python data/seed.py
```

### 4. Run the Application

```bash
python run.py
```

The app will be available at: **http://localhost:5000**

## Usage

1. **Register**: Create an account at `/auth/register`
2. **Browse Products**: View all products at `/products/`
3. **Search & Filter**: Use category tabs and search bar
4. **Add to Favorites**: Click the heart icon on products
5. **Leave Reviews**: Rate products on the detail page
6. **Chat with AI**: Click the chat icon (bottom-right) to:
   - Ask about products
   - Get recommendations
   - Place orders through conversation

## Project Structure

```
ecommerce/
├── app/
│   ├── __init__.py         # Flask app factory
│   ├── models.py           # Database models
│   ├── routes/             # API endpoints
│   │   ├── auth.py         # Authentication
│   │   ├── products.py     # Products & reviews
│   │   ├── orders.py       # Order management
│   │   └── chatbot.py      # RAG chatbot
│   ├── services/
│   │   └── rag_service.py  # LangChain integration
│   ├── static/             # CSS & JavaScript
│   └── templates/          # HTML templates
├── data/
│   ├── products.json       # Sample products
│   └── seed.py             # Database seeder
├── config.py
├── run.py
└── requirements.txt
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET/POST | User login |
| `/auth/register` | GET/POST | User registration |
| `/products/` | GET | List products |
| `/products/<id>` | GET | Product details |
| `/products/<id>/review` | POST | Add review |
| `/products/<id>/favorite` | POST | Toggle favorite |
| `/orders/` | GET | List orders |
| `/orders/create` | POST | Create order |
| `/chat/message` | POST | Send chat message |
| `/chat/order-verify` | POST | Verify/confirm order |
