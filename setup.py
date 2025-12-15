from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("app/requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="legaltech-suite",
    version="4.0.0",
    author="LegalTech Chile",
    author_email="contacto@legaltech.cl",
    description="Sistema de sanitización documental con IA para el sector legal chileno",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ALONSO-JR/legaltech",
    packages=find_packages(include=['app', 'app.*']),
    package_dir={'': '.'},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Legal Industry",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Filters",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "flake8>=6.0.0",
            "black>=23.0.0",
            "mypy>=1.7.0",
            "bandit>=1.7.5",
            "twine>=4.0.0",
            "build>=1.0.0",
        ],
        "ocr": [
            "ocrmypdf>=15.0.0",
            "pytesseract>=0.3.10",
            "pdf2image>=1.16.3",
            "pillow>=10.1.0",
        ],
        "ml": [
            "torch>=2.1.0",
            "transformers>=4.35.2",
            "sentencepiece>=0.1.99",
            "datasets>=2.15.0",
        ],
        "api": [
            "gunicorn>=21.2.0",
            "httpx>=0.25.0",
            "python-jose>=3.3.0",
            "passlib>=1.7.4",
        ],
        "dashboard": [
            "streamlit-aggrid>=0.3.4",
            "streamlit-option-menu>=0.3.6",
            "streamlit-authenticator>=0.2.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "legaltech=app.main:main",
            "legaltech-dashboard=app.streamlit_app:main",
            "legaltech-api=app.api_app:main",
            "legaltech-process=app.main:ejecutar_modo_directo",
            "legaltech-test=app.main:ejecutar_pruebas",
        ],
    },
    package_data={
        "app": [
            "*.py",
            "*.yaml",
            "*.json",
            "*.md",
            "templates/*",
            "static/images/*",
            "tests/*.py",
        ],
    },
    include_package_data=True,
    data_files=[
        ("config", ["config.yaml"]),
        ("docs", ["README.md"]),
        ("examples", ["examples/sample_contract.pdf"]),
    ],
    keywords=[
        "legal",
        "chile",
        "privacy",
        "document",
        "redaction",
        "ai",
        "nlp",
        "ocr",
        "compliance",
        "gdpr",
        "data protection",
        "anonymization",
        "sanitization",
    ],
    project_urls={
        "Documentation": "https://legaltech-suite.readthedocs.io/",
        "Source": "https://github.com/ALONSO-JR/legaltech",
        "Tracker": "https://github.com/ALONSO-JR/legaltech/issues",
        "Changelog": "https://github.com/ALONSO-JR/legaltech/releases",
    },
    license="MIT",
    platforms=["Linux", "Windows", "macOS"],
    zip_safe=False,
)