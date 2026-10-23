# Local PostgreSQL/PostGIS setup

Install PostgreSQL with the PostGIS extension, create a database, enable `postgis`, and add a `LOCAL_DATABASE_URL` entry to the root `.env`. Keep this URL server-side only.

Use `scripts/restore_postgres.ps1 -DumpFile <dump> -TargetDatabaseUrl <url>` to restore a Supabase backup into the local instance. Import large OSM graphs with the existing graph import tools and run the graph validator before making a snapshot selectable. Store raw archives outside Git under the local data directory.

The local database is required for bulk geospatial storage; Supabase remains the operational cloud store. A local machine is not a production high-availability deployment, so a managed PostGIS VM or managed database is required before public deployment.
