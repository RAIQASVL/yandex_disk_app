# yandex_disk_app
Django web application that interacts with the Yandex Disk API.

# Yandex.Disk Browser

A Django web application that allows users to browse and download files from public Yandex.Disk links. The application features user authentication, file browsing, and bulk download capabilities.

## Features

- 🔐 User Authentication (Login/Signup/Logout)
- 📁 Browse Yandex.Disk public folders
- 🔍 Filter files by type (documents, images, videos, audio)
- ⬇️ Download single or multiple files
- 📦 Bulk download with ZIP compression
- 💾 File caching for better performance
- 🎨 Modern, responsive Bootstrap UI

## Prerequisites

- Python 3.10+
- pip (Python package installer)
- Git
- Yandex.Disk OAuth Token

## Installation

1. Clone the repository:
```bash
git clone https://github.com/RAIQASVL/yandex_disk_app.git
cd yandex_disk_browser
```

2. Create and activate a virtual environment:
```bash
# For macOS/Linux
python -m venv .venv
source .venv/bin/activate

# For Windows
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root directory with:
```env
DJANGO_SECRET_KE=your_django_secret_key
DEBUG=True
YANDEX_OAUTH_TOKEN=your_yandex_disk_oauth_token
```

5. Apply database migrations:
```bash
python manage.py migrate
```

6. Create a superuser (admin):
```bash
python manage.py createsuperuser
```

7. Run the development server:
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Environment Variables

- `DJANGO_SECRET_KEY`: Django secret key for security
- `DEBUG`: Boolean for debug mode
- `YANDEX_OAUTH_TOKEN`: Your Yandex.Disk OAuth token
- `ALLOWED_HOSTS`: List of allowed hosts (optional)

## Getting Yandex.Disk OAuth Token

1. Go to [Yandex OAuth](https://yandex.com/dev/disk/api/concepts/oauth.html)
2. Register your application
3. Get your OAuth token
4. Add the token to your `.env` file

## Project Structure

```
yandex_disk_app/
├── yandex_disk/                 # Project configuration
├── apps/                   # Source code
│   ├── core/             # Core app (auth, common functionality)
│   │   ├── templates/    # Auth templates
│   │   ├── forms.py
│   │   └── views.py
│   ├── disk/            # Disk browser app
│   │   ├── templates/   # Disk browser templates
│   │   ├── services/    # Disk and cache services
│   │   └── views.py
│   └── templates/       # Base templates
├── manage.py
├── requirements.txt
└── README.md
```

## Usage

1. Log in or create a new account
2. Paste a Yandex.Disk public folder link
3. Browse and filter files
4. Download individual files or select multiple files for bulk download

## Development

- Follow PEP 8 style guide
- Write tests for new features
- Update requirements.txt when adding new packages

## Testing

Run tests with:
```bash
python manage.py test
```

## Common Issues

1. Template Not Found Error:
   - Check template directories in settings.py
   - Verify template file locations

2. Authentication Issues:
   - Verify YANDEX_OAUTH_TOKEN is set
   - Check token permissions

3. Download Issues:
   - Verify file permissions
   - Check disk space for ZIP creation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Django Framework
- Bootstrap
- Yandex.Disk API

## Authors

- Ioann Jeanlao Gorvier - Initial work

## Support

For support, email raiqasvl@gmail.com or create an issue in the repository.