from setuptools import setup, find_packages

setup(
    name="lab-reader",
    version="3.0.0",
    description="Univerzalni parser za laboratorijske nalaze sa OCR podrškom",
    author="Micko666",
    author_email="micko@example.com",
    packages=find_packages(),
    install_requires=[
        "streamlit>=1.50.0",
        "pandas>=2.0.0",
        "pdfplumber>=0.11.0",
        "PyPDF2>=3.0.0",
        "xlsxwriter>=3.2.0",
        "pymupdf>=1.26.0",
        "pytesseract>=0.3.13",
        "Pillow>=10.4.0",
    ],
    entry_points={
        "console_scripts": [
            "lab-reader=app_v3:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
