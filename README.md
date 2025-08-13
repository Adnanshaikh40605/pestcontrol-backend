# PestControl99 Backend

A Django REST API backend for pest control management system.

## Features

- User authentication and authorization
- Client management
- Job card management
- Service tracking
- RESTful API endpoints

## Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/adnandoh/pestcontrol99-Backend-.git
cd pestcontrol99-Backend-
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp env.example .env
# Edit .env file with your configuration
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

## API Documentation

See `API_TESTING_GUIDE.md` for detailed API documentation and testing instructions.

## Project Structure

- `backend/` - Main Django application
- `core/` - Core Django settings and configuration
- `requirements.txt` - Python dependencies
- `manage.py` - Django management script

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.