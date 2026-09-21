# TCG Web

Tienda de cartas Pokémon TCG con Django 5.2, SQLite y catálogo de TCGdex.
`Set` y `Card` guardan información externa; `Product` mantiene SKU, idioma,
condición, variante, descripción, precio y stock propios de la tienda.

## Funcionalidades

- Importación repetible de cartas y sets, sin duplicados ni cambios de precio/stock.
- Catálogo con búsqueda, filtros por set y disponibilidad, orden y 12 productos por página.
- Detalle por producto, selector de otras versiones y compatibilidad con enlaces antiguos de cartas.
- Carrito por sesión: agregar, actualizar y quitar; precios y stock consultados en el servidor.
- Administración con imágenes opcionales, búsqueda por SKU y filtros por versión.
- Protección del catálogo frente a borrados accidentales y restricción de precios no negativos.
- Pruebas automáticas y GitHub Actions.

El carrito **no reserva ni descuenta stock**. Pedidos, checkout y pagos aún no están
implementados. No se deben aceptar ventas desde este flujo hasta completar esa etapa.

## Instalación local (Windows / PowerShell)

Requiere Python 3.12. Desde la carpeta del repositorio:

```powershell
git switch strengthen
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copia la clave generada al valor `DJANGO_SECRET_KEY` de `.env`.
Conserva `DJANGO_DEBUG=true` solo en desarrollo. Si ya tienes `.env`, edítalo sin
sobrescribir tus valores. Nunca subas `.env` ni claves al repositorio.

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre http://127.0.0.1:8000/ y http://127.0.0.1:8000/admin/.
En macOS/Linux activa el entorno con `source venv/bin/activate` y copia el ejemplo
con `cp .env.example .env`; los comandos Python son iguales.

## Actualizar una instalación existente

1. Detén el servidor y respalda `db.sqlite3` antes de aplicar migraciones.
2. Instala `requirements.txt` y configura `.env` con una **clave nueva**: la anterior
   estaba incluida en el código público. El cambio puede invalidar sesiones existentes.
3. Ejecuta `python manage.py migrate`.
4. En el administrador completa idioma, condición y variante. Los productos previos
   quedan en **Por definir**, sin asumir su estado; cada uno recibe un SKU único.

La migración `0003` conserva precio, stock, descripción y vínculos existentes.
Si encuentra precios negativos se detiene con un mensaje: corrígelos y repite.
Los productos antiguos sin carta se conservan para revisión, pero no se muestran
ni pueden agregarse al carrito. Asóciales una carta desde el administrador.
No borres las migraciones anteriores ni recrees la base de datos para actualizar.

## Cargar el catálogo

```powershell
python manage.py import_card base1-4
python manage.py import_set base1 --limit 5
python manage.py import_set base1
```

La fuente de metadatos se mantiene en **inglés** (`/v2/en`); el idioma del producto
representa la carta física y se configura por separado. Importar una carta no crea
un producto a la venta: créalo en el administrador y fija precio, stock y versión.
Se permiten varias ofertas de una carta con SKU distintos.

El servicio en `products/services/tcgdex.py` valida IDs, campos y URLs, aplica un
límite de 15 segundos a cada solicitud y hasta 3 intentos ante errores de red,
HTTP 429 o errores transitorios del servidor. Cada carta y su set se guardan en
una transacción; las llamadas HTTP ocurren antes de abrirla.

`import_set` consulta el detalle de cada carta. Si alguna falla, continúa con las
restantes y termina con un resumen y código de error. Las cartas correctas se
conservan. Repite el comando para reintentar; no se duplica el catálogo ni se altera
el inventario comercial. Los sets existentes también actualizan sus metadatos.

Referencia del formato externo: [carta](https://tcgdex.dev/rest/card) y
[set](https://tcgdex.dev/rest/set).

## Rutas

| Ruta | Función |
| --- | --- |
| `/` | Catálogo; parámetros `q`, `set`, `in_stock=1`, `sort` y `page` |
| `/products/<id>/` | Detalle de un producto específico |
| `/cards/<tcgdex_id>/` | Enlace antiguo: redirige si hay un producto o muestra versiones |
| `/cart/` | Carrito de la sesión actual |
| `/cart/add/<id>/` | Agregar cantidad mediante POST y CSRF |
| `/cart/update/<id>/` | Reemplazar cantidad mediante POST y CSRF |
| `/cart/remove/<id>/` | Quitar producto mediante POST y CSRF |
| `/admin/` | Administración |

Órdenes válidos: `newest`, `price_asc`, `price_desc`, `name`.
El carrito almacena únicamente IDs y cantidades. Si cambia el stock, muestra una
advertencia para ajustar la cantidad; si se elimina o desvincula el producto,
lo retira del carrito. Los totales usan `Decimal` y el precio actual de la base.

## Verificación

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Las pruebas cubren la migración de inventario existente, variantes y rutas,
búsqueda/paginación, imágenes ausentes, restricciones, sesión/CSRF, cambios de
precio/stock e importaciones repetidas, inválidas y parcialmente fallidas.
La API externa se simula en las pruebas para que no dependan de disponibilidad
ni modifiquen catálogos remotos.

## Configuración para despliegue

| Variable | Uso |
| --- | --- |
| `DJANGO_SECRET_KEY` | Obligatoria; generar una nueva por entorno |
| `DJANGO_DEBUG` | `true` solo local; por defecto `false` |
| `DJANGO_ALLOWED_HOSTS` | Hosts separados por comas, sin esquema |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS confiables separados por comas, si se requieren |

Con `DEBUG=false` se habilitan cookies seguras, redirección HTTPS y HSTS de un año
(solo el dominio actual). Configura HTTPS y el servidor de estáticos antes de
publicar: `python manage.py collectstatic --noinput`. Si usas un proxy que termina
TLS, configura el encabezado de protocolo seguro **según ese proveedor y solo
si el proxy elimina encabezados enviados por el cliente**; no se confía en un
encabezado arbitrario por defecto.

La configuración conserva SQLite para desarrollo. Este cambio no despliega el
sitio ni configura una pasarela de pago. Antes de habilitar pedidos se necesita
validación final de precios/stock, actualización atómica de inventario y una
integración de pagos con confirmación verificable e idempotente.
