# TCG Web

A web application for managing and selling Pokémon TCG cards, built with **Django** and integrated with the **TCGdex API**.

The project separates external card information from the store's own inventory, prices, and products, allowing the catalog to be managed efficiently without storing the entire TCGdex database locally.

---

## 🚀 Features

* 🃏 Pokémon TCG card catalog
* 🔎 Card information retrieved from TCGdex
* 🖼️ Card images provided by TCGdex
* 📦 Set and card management
* 💰 Product price management
* 📊 Stock management
* 🔗 Relationship between cards and store products
* ⚙️ Django Admin management panel
* 📥 Import cards directly from TCGdex using Django management commands
* 💾 SQLite database for development

---

## 🏗️ Project Architecture

The project uses the following structure:

```text
TCGdex API
     │
     ▼
    Set
     │
     ▼
    Card
     │
     ▼
   Product
     │
     ├── Price
     ├── Stock
     └── Description
```

### Main models

| Model     | Description                                             |
| --------- | ------------------------------------------------------- |
| `Set`     | Pokémon TCG expansion or set                            |
| `Card`    | Individual Pokémon TCG card and its TCGdex information  |
| `Product` | Store product with its own price, stock and description |

This structure allows TCGdex to provide the card catalog information while the application manages its own commercial data.

---

## 🛠️ Technologies

* **Python**
* **Django**
* **SQLite**
* **TCGdex API**
* **HTML / CSS**
* **Git & GitHub**

---

## 📁 Project Structure

```text
tcg-web/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── products/
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── import_card.py
│   │
│   ├── admin.py
│   ├── models.py
│   ├── views.py
│   └── ...
│
├── manage.py
├── db.sqlite3
├── README.md
└── .gitignore
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/Smsidler/tcg-web.git
cd tcg-web
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### 3. Activate the virtual environment

#### Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

#### Windows CMD

```cmd
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install django
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

Django Admin:

```text
http://127.0.0.1:8000/admin/
```

---

## 🃏 Importing Cards from TCGdex

Cards can be imported directly from TCGdex using a Django management command.

For example:

```bash
python manage.py import_card base1-4
```

This imports the card inform
