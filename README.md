# TCG Web

Tienda web de cartas Pokémon TCG desarrollada con Django.

El proyecto utiliza **TCGdex** como fuente externa del catálogo de cartas, mientras que la información comercial de cada producto —como SKU, idioma, condición, variante, precio y stock— se administra de forma independiente dentro de la tienda.

La aplicación utiliza **PostgreSQL en Neon** como base de datos y almacenamiento de imágenes mediante un servicio **S3-compatible / Neon Object Storage**.

## Funcionalidades

- Importación de cartas y sets desde TCGdex.
- Importaciones repetibles sin duplicar cartas ni alterar precio o stock.
- Catálogo con búsqueda de productos.
- Filtro por set.
- Filtro por disponibilidad.
- Orden por fecha, precio y nombre.
- Paginación de productos.
- Detalle individual de cada producto.
- Varias versiones comerciales de una misma carta.
- Carrito basado en sesión.
- Validación de cantidades y stock en el servidor.
- Checkout.
- Creación de pedidos.
- Items de pedido con snapshot del precio de compra.
- Descuento automático de inventario al crear un pedido.
- Restauración automática del stock al cancelar un pedido.
- Nuevo descuento del stock al reactivar un pedido cancelado.
- Operaciones de inventario protegidas mediante transacciones.
- Confirmación de pedidos mediante UUID público.
- Protección de la página de confirmación mediante sesión.
- Administración de pedidos desde Django Admin.
- Imágenes personalizadas para cartas.
- Object Storage compatible con S3.
- Protección del catálogo frente a borrados accidentales.
- Validación de precios no negativos.
- Suite automatizada de 45 tests.

> La creación de pedidos y el control de inventario ya están implementados. La integración con una pasarela de pago todavía está pendiente, por lo que el proyecto no debe considerarse una tienda con pagos online completos hasta incorporar y verificar ese flujo.

---

## Tecnologías

- Python
- Django 5.2
- PostgreSQL
- Neon
- Neon Object Storage / S3
- TCGdex API
- Pillow
- django-storages
- boto3
- dj-database-url

---

## Arquitectura del catálogo

El proyecto separa los datos externos del catálogo de los datos comerciales de la tienda.

### Set

Representa una expansión o set de Pokémon TCG.

La información puede provenir de TCGdex.

### Card

Representa una carta del catálogo.

Contiene información como:

- ID de TCGdex
- nombre
- número local
- rareza
- ilustrador
- imagen
- set

Una carta también puede tener una imagen personalizada almacenada en Object Storage.

### Product

Representa una versión de una carta que realmente está a la venta.

Mantiene información propia de la tienda:

- SKU
- idioma
- condición
- variante
- descripción
- precio
- stock

Una misma `Card` puede tener varios `Product`.

Esto permite vender, por ejemplo, la misma carta en distintos idiomas, condiciones o variantes sin duplicar la información del catálogo.

---

## Pedidos e inventario

El carrito almacena únicamente IDs de productos y cantidades dentro de la sesión.

Agregar un producto al carrito **no reserva ni descuenta stock**.

El inventario se modifica al completar correctamente el checkout.

Durante la creación de un pedido:

1. Los productos se vuelven a consultar desde la base de datos.
2. Se comprueba nuevamente el stock disponible.
3. El total se calcula utilizando los precios almacenados en el servidor.
4. Se crea el pedido.
5. Se crean los `OrderItem`.
6. Se descuenta el inventario.
7. La operación se ejecuta dentro de una transacción.

La lógica principal se encuentra centralizada en:

```text
products/services/orders.py
```

Esto permite reutilizar la misma lógica desde vistas, administración y futuras integraciones como pagos o webhooks.

### Cancelación

Cuando un pedido se cancela, el stock se restaura automáticamente.

El sistema utiliza `stock_restored` para impedir que una cancelación repetida pueda devolver el mismo inventario más de una vez.

### Reactivación

Si un pedido cancelado vuelve a un estado activo, el sistema comprueba primero que exista suficiente inventario.

Solo después de validar todos los productos vuelve a descontar las unidades.

---

## Seguridad de pedidos

Cada pedido posee un identificador público UUID independiente del ID interno de la base de datos.

Ejemplo:

```text
/orders/<uuid>/success/
```

La página de confirmación también comprueba que el pedido haya sido creado desde la sesión actual.

Esto evita exponer pedidos utilizando IDs numéricos consecutivos y dificulta el acceso a información de otros clientes.

---

## Instalación local

### Windows / PowerShell

Clona el repositorio y entra al proyecto.

Crea el entorno virtual:

```powershell
python -m venv venv
```

Actívalo:

```powershell
.\venv\Scripts\Activate.ps1
```

Instala las dependencias:

```powershell
python -m pip install -r requirements.txt
```

Crea tu archivo de variables de entorno:

```powershell
Copy-Item .env.example .env
```

Genera una clave secreta:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copia el resultado en:

```text
DJANGO_SECRET_KEY
```

dentro de `.env`.

Nunca subas `.env`, contraseñas, tokens o claves privadas al repositorio.

---

## Base de datos

La aplicación puede conectarse a PostgreSQL mediante:

```text
DATABASE_URL
```

Ejemplo de estructura:

```text
postgresql://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

Las credenciales reales deben almacenarse únicamente en `.env` o en las variables de entorno de la plataforma de despliegue.

Aplica las migraciones:

```powershell
python manage.py migrate
```

Crea un administrador:

```powershell
python manage.py createsuperuser
```

---

## Object Storage

Las imágenes personalizadas pueden almacenarse en un servicio compatible con S3.

Variables utilizadas:

```text
AWS_ENDPOINT_URL_S3
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
AWS_STORAGE_BUCKET_NAME
```

Las credenciales reales nunca deben guardarse en Git.

Los archivos almacenados localmente antes de configurar Object Storage no se migran automáticamente.

---

## Ejecutar el servidor

```powershell
python manage.py runserver
```

Aplicación:

```text
http://127.0.0.1:8000/
```

Administración:

```text
http://127.0.0.1:8000/admin/
```

---

## Importar cartas desde TCGdex

Importar una carta:

```powershell
python manage.py import_card base1-4
```

Importar algunas cartas de un set:

```powershell
python manage.py import_set base1 --limit 5
```

Importar un set:

```powershell
python manage.py import_set base1
```

La fuente del catálogo se mantiene en inglés.

El idioma configurado en `Product` representa el idioma de la carta física que se está vendiendo.

Importar una carta **no crea automáticamente un producto a la venta**.

Después de importar la carta, el producto comercial se crea desde el administrador configurando:

- precio
- stock
- idioma
- condición
- variante

---

## Servicio TCGdex

La integración se encuentra principalmente en:

```text
products/services/tcgdex.py
```

El servicio:

- valida IDs;
- valida campos recibidos;
- valida URLs;
- utiliza un timeout limitado;
- reintenta errores transitorios;
- evita modificar productos comerciales;
- utiliza transacciones para cambios del catálogo.

Las importaciones repetidas no deben duplicar cartas ni modificar precio o inventario de `Product`.

---

## Rutas principales

| Ruta | Función |
| --- | --- |
| `/` | Catálogo |
| `/products/<id>/` | Detalle de producto |
| `/cards/<tcgdex_id>/` | Compatibilidad con enlaces de cartas |
| `/cart/` | Carrito |
| `/cart/add/<id>/` | Agregar producto |
| `/cart/update/<id>/` | Actualizar cantidad |
| `/cart/remove/<id>/` | Eliminar del carrito |
| `/checkout/` | Checkout |
| `/orders/<uuid>/success/` | Confirmación protegida del pedido |
| `/admin/` | Administración Django |

El catálogo acepta parámetros como:

```text
q
set
in_stock
sort
page
```

Opciones de orden:

```text
newest
price_asc
price_desc
name
```

---

## Tests

El proyecto dispone actualmente de **45 tests automatizados**.

Ejecuta:

```powershell
python manage.py test
```

También puedes comprobar la configuración:

```powershell
python manage.py check
```

Y comprobar si existen cambios de modelos sin migración:

```powershell
python manage.py makemigrations --check --dry-run
```

Los tests cubren, entre otros:

- modelos;
- restricciones de base de datos;
- catálogo;
- carrito;
- sesiones;
- CSRF;
- importación desde TCGdex;
- checkout;
- creación de pedidos;
- cálculo de precios en servidor;
- reducción de stock;
- protección de confirmaciones de pedido;
- UUID público;
- cancelación de pedidos;
- restauración de inventario;
- prevención de restauración doble;
- reactivación de pedidos;
- validación de stock al reactivar.

Durante los tests se utiliza una base SQLite local separada para evitar crear o eliminar bases de prueba dentro de Neon.

---

## Variables de entorno

### Django

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS
DJANGO_CSRF_TRUSTED_ORIGINS
```

### Base de datos

```text
DATABASE_URL
```

### Object Storage

```text
AWS_ENDPOINT_URL_S3
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
AWS_STORAGE_BUCKET_NAME
```

Nunca almacenes valores reales de producción en `.env.example`.

---

## Estado actual

Actualmente están implementados:

```text
TCGdex
    ↓
Catálogo
    ↓
Product
    ↓
Carrito
    ↓
Checkout
    ↓
Order + OrderItem
    ↓
Control transaccional de inventario
```

La base de datos utiliza PostgreSQL administrado y las imágenes personalizadas pueden almacenarse mediante Object Storage compatible con S3.

---

## Próximas etapas

Las siguientes etapas previstas son:

1. Preparación del proyecto para producción.
2. Despliegue.
3. Configuración de archivos estáticos.
4. Sistema de despacho/retiro.
5. Integración de pagos.
6. Webhooks de confirmación de pago.
7. Emails transaccionales.
8. Cuentas de clientes e historial de pedidos.
9. Wishlist y avisos de reposición.
10. Dashboard administrativo y alertas de stock.

---

## Importante

Este proyecto todavía está en desarrollo.

Antes de utilizarlo como tienda real deben completarse y verificarse especialmente:

- despliegue de producción;  
- configuración HTTPS;
- sistema de despacho;
- integración de pagos;
- confirmación segura e idempotente de pagos;
- emails transaccionales;
- pruebas de integración en PostgreSQL.