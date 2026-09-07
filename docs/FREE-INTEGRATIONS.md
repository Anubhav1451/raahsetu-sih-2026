# Free integration plan

- **Weather:** Open-Meteo is keyless for this prototype. The API exposes `/api/v1/weather?lat=…&lon=…` and maps heavy precipitation or wind to the existing `heavy_rain` route scenario.
- **Notifications:** browser notifications and the in-app alert feed are free. Web Push can be added after the app has an HTTPS origin and a generated VAPID key pair; SMS and WhatsApp are not reliably free.
- **Database:** the existing Supabase free project is sufficient for reviewed metadata, alerts, fleet rows and delivery jobs. Keep large OSM snapshots in versioned VM/object storage.
- **Hosting:** local demo needs no paid service. A public deployment needs an HTTPS-capable free tier or team-provided VM; Kubernetes itself should be treated as an environment milestone, not assumed free.
