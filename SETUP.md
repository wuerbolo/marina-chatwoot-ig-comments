# Setup manual: Comentarios IG → Chatwoot

Esta guía cubre todo lo que hay que configurar fuera del código: Meta App, Chatwoot,
base de datos (Neon) y despliegue en la VPS con Docker + NPM. El código ya está listo en
este repo; aquí solo se documentan los pasos manuales en cada panel.

## 0. Checklist rápido

- [ ] Confirmar si el canal de Instagram DM actual usa Instagram Business Login o Facebook
      Login for Business (paso 1)
- [ ] Añadir permiso `instagram_manage_comments` a la Meta App y pasar App Review si hace
      falta (paso 1)
- [ ] Suscribir el webhook `comments` (paso 2)
- [ ] Crear proyecto Neon nuevo + base de datos (paso 3)
- [ ] Crear inbox API "Comentarios IG" en Chatwoot + webhook saliente (paso 4)
- [ ] Rellenar `.env` en la VPS (paso 5.1)
- [ ] Conectar el contenedor a la red de NPM y crear el Proxy Host (paso 5.2)
- [ ] Probar con el simulador de webhooks de Meta (paso 6)

## 1. Meta App: confirmar tipo de login y permisos

### 1.1 Averiguar qué flujo de login usa el canal de Instagram DM actual

Necesitamos saberlo porque determina qué token reutilizar y si hay que re-consentir
permisos. Dos formas de comprobarlo, de más a menos directa:

1. **developers.facebook.com** → *Mis Apps* → la app que usa el canal de Instagram DM de
   Chatwoot → menú lateral de productos:
   - Si aparece **"Instagram" → "API setup with Instagram login"** → es **Instagram
     Business Login** (flujo sin Página de Facebook, token contra `graph.instagram.com`).
   - Si aparece **"Facebook Login for Business"** + Webhooks configurados sobre un objeto
     Página → es el flujo **clásico vía Página de Facebook** (token de Página, contra
     `graph.facebook.com`).
2. **Chatwoot** → Settings → Inboxes → el inbox de Instagram DM actual → Configuration:
   suele indicar si está conectado como cuenta de Instagram directa o vía Página vinculada.

Si acaba siendo Facebook Login for Business, además del `IG_LONG_LIVED_ACCESS_TOKEN`
necesitaréis el `page_id` de la Página vinculada y el permiso `pages_read_engagement` ya
mencionado en el spec (sección 3.1).

### 1.2 Permisos a añadir a la App

En el mismo panel de la App (App Review → Permisos y funciones):

- `instagram_manage_comments` (nuevo, es el que falta)
- `instagram_manage_messages` (ya debería estar activo, es el que habilita
  `private_replies`)
- `instagram_business_basic`
- `pages_read_engagement` (solo si el flujo es Facebook Login for Business, ver 1.1)

Si la app ya pasó App Review para mensajería, probablemente solo falte re-someter para
`instagram_manage_comments`. Cuenta con que puede tardar de días a un par de semanas y
puede pedir verificación de negocio si no la tenéis ya. Chatwoot tiene una plantilla de
review que se puede adaptar: `developers.chatwoot.com/self-hosted/instagram-app-review`.

Si la cuenta de Instagram sobre la que vais a operar es la misma que administra la App
(modo desarrollo), puede que no haga falta pasar review todavía para probar — confirmar
en el propio panel al intentar activar el permiso.

## 2. Suscripción al webhook de Meta

Una vez desplegado el servicio (paso 5) y con `META_VERIFY_TOKEN` fijado, suscribe el
campo `comments`:

```bash
curl -X POST "https://graph.facebook.com/v21.0/{app-id}/subscriptions" \
  -d "object=instagram" \
  -d "callback_url=https://ig-comments.tudominio.com/webhooks/meta/instagram" \
  -d "verify_token=<el mismo valor que META_VERIFY_TOKEN en tu .env>" \
  -d "fields=comments" \
  -d "access_token=<token de la App (app_id|app_secret) o token de admin>"
```

Meta llamará primero a `GET .../webhooks/meta/instagram` con el handshake; el servicio ya
lo gestiona (`app/routers/meta_webhook.py`). Si la suscripción falla, revisa que el
dominio ya tenga HTTPS válido (ver paso 5.2) antes de reintentar.

## 3. Base de datos: Neon

**Recomendación: proyecto Neon nuevo y separado** del que usa Chatwoot, no una tabla más
en esa base. Motivos:
- Aísla credenciales: este servicio solo necesita acceso a su propia tabla, no a los datos
  de producción de Chatwoot.
- Evita cualquier riesgo de migraciones/consultas de esta app afectando al rendimiento o
  esquema de la base de Chatwoot.
- El volumen de esta tabla es mínimo (una fila por comentario) — sobra con el free tier de
  Neon, así que no hay ahorro real en compartir proyecto.

Pasos:
1. En el dashboard de Neon → *New Project* → nómbralo p. ej. `ig-comments`.
2. Neon crea una base de datos por defecto (`neondb`) — vale, no hace falta crear otra.
3. Copia el *connection string* (con `sslmode=require`) desde *Connection Details* y
   pégalo en `DATABASE_URL` en el `.env` del servicio.
4. No hace falta crear la tabla a mano: el servicio la crea sola al arrancar
   (`Base.metadata.create_all()` en `app/db.py`).

**Sobre backups**: Neon ya hace point-in-time recovery y snapshots automáticos a nivel de
plataforma, independientemente de vuestro pipeline de rclone + Backblaze. Ese pipeline
respalda volúmenes/ficheros locales de Docker en la VPS — este servicio no tiene volumen
persistente (todo el estado vive en Neon), así que en principio **no hace falta añadirlo**
al backup de rclone. Lo único que valdría la pena respaldar ahí es el propio `.env` (los
secretos), si no lo tenéis ya versionado en vuestro gestor de secretos habitual.

## 4. Chatwoot: inbox y webhook

### 4.1 Crear el inbox "Comentarios IG"

Settings → Inboxes → Add Inbox → **API** (no "Instagram" — ese es el tipo que ya usa el
canal de DM nativo; aquí queremos un inbox de tipo API genérico, como indica el spec
sección 3.4).
- Nombre: `Comentarios IG`.
- Al terminar, copia el `inbox_id` (visible en la URL del inbox o en Settings) →
  `CHATWOOT_INBOX_ID_COMENTARIOS`.

### 4.2 Token de API

Profile → Access Token de un usuario de servicio (o el token de la cuenta) →
`CHATWOOT_API_ACCESS_TOKEN`. Anota también el `account_id` de la URL → `CHATWOOT_ACCOUNT_ID`.

### 4.3 Webhook saliente

**No uses el webhook de cuenta** (Settings → Integrations → Webhooks). Ese dispara para
todos los inboxes de la cuenta y obliga a filtrar por `inbox_id` en el código — y si algún
día hay más de un inbox de tipo API, mezclaría eventos de todos por el mismo canal.

Usa en su lugar el webhook propio del inbox "Comentarios IG":

- Settings → Inboxes → Comentarios IG → Configuration → **Webhook URL**:
  `https://ig-comments.tudominio.com/webhooks/chatwoot/outgoing`

Este webhook solo se dispara para eventos de este inbox (Chatwoot lo restringe a
`channel_type == 'Channel::Api'`), así que no hace falta ningún filtro adicional.

El secreto de firma **no se muestra en esa pantalla** (Chatwoot solo enseña ahí el
`hmac_token`, que es para otra cosa: validar `identifier_hash` de contactos creados por
esta misma API, no para firmar el webhook saliente). Hay que pedirlo por API, como
administrador de la cuenta:

```bash
curl -s -H "api_access_token: $CHATWOOT_API_ACCESS_TOKEN" \
  "$CHATWOOT_BASE_URL/api/v1/accounts/$CHATWOOT_ACCOUNT_ID/inboxes/$CHATWOOT_INBOX_ID_COMENTARIOS" \
  | grep -o '"secret":"[^"]*"'
```

Copia ese valor en `CHATWOOT_INBOX_WEBHOOK_SECRET`. Si alguna vez hay que rotarlo, existe
`POST .../inboxes/{id}/reset_secret`.

## 5. Despliegue en la VPS

### 5.1 Variables de entorno

Copia `.env.example` a `.env` en la carpeta del proyecto en la VPS y rellena todos los
valores recogidos en los pasos 1–4.

### 5.2 Red Docker con NPM

NPM (Nginx Proxy Manager) es el reverse proxy: termina TLS y redirige por
subdominio/subruta al contenedor correspondiente. Para que NPM pueda hablar con este
contenedor sin publicar el puerto al host:

1. Averigua la red Docker donde corre NPM: `docker network ls` en la VPS (busca algo tipo
   `npm_default` o `proxy`).
2. Edita `docker-compose.yml` de este proyecto y cambia `external: true` con el nombre real
   de esa red en la sección `networks.npm_network` (o renombra la clave si prefieres usar
   el nombre real directamente).
3. `docker compose up -d --build`.
4. En la UI de NPM → *Proxy Hosts* → *Add Proxy Host*:
   - Domain: `ig-comments.tudominio.com` (el que decidáis)
   - Forward Hostname/IP: `ig-comments-service` (el nombre del contenedor, ya que está en
     la misma red Docker que NPM)
   - Forward Port: `8000`
   - Pestaña SSL: pide certificado Let's Encrypt, fuerza HTTPS.

Si preferís probar antes sin NPM (acceso directo por IP:puerto durante desarrollo),
descomenta el bloque `ports: - "8000:8000"` en el compose.

### 5.3 Arrancar

```bash
docker compose up -d --build
docker compose logs -f ig-comments-service
```

Confirma `GET https://ig-comments.tudominio.com/health` → `{"status": "ok"}`.

## 6. Pruebas

1. **Handshake de Meta**: tras suscribir el webhook (paso 2), Meta ya debería haber
   verificado el endpoint. Si quieres probarlo a mano:
   `curl "https://ig-comments.tudominio.com/webhooks/meta/instagram?hub.mode=subscribe&hub.verify_token=<tu-token>&hub.challenge=test123"`
   → debe devolver `test123`.
2. **Simulador de Meta for Developers**: panel de la App → Webhooks → Test → dispara un
   evento `comments` de prueba y comprueba en `docker compose logs` que se procesa y que
   aparece el ticket en el inbox "Comentarios IG" de Chatwoot.
3. **Private reply**: responde desde ese ticket en Chatwoot y confirma en los logs que se
   llama a `private_replies` y que el ticket se auto-resuelve.
4. **Guardrails**: intenta responder una segunda vez en el mismo ticket ya resuelto —
   debe aparecer la nota interna de "ya se envió un privado", sin llamar a Meta de nuevo
   (cubierto también por los tests automáticos en `tests/test_reply_guardrails.py`).

## 7. Pendiente / a definir con Marina y Carmen

- Confirmar tipo de login de Meta (paso 1.1) antes de pedir los permisos nuevos.
- Decidir si el simulador de Meta basta para el primer ciclo de pruebas o si hace falta
  probar con comentarios reales en la cuenta de producción.
