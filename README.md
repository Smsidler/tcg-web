# TCG Web
# 🃏 TCG Web

[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-green?logo=django)](https://www.djangoproject.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-blue?logo=sqlite)](https://www.sqlite.org/)
[![TCGdex](https://img.shields.io/badge/API-TCGdex-purple)](https://tcgdex.dev/)
[![Status](https://img.shields.io/badge/Status-In%20Development-orange)](https://github.com/Smsidler/tcg-web)

A web application for managing and selling Pokémon TCG cards, built with Django and integrated with the TCGdex API.

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
