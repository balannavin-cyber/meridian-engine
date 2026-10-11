DO $$BEGIN CREATE ROLE anon; EXCEPTION WHEN duplicate_object THEN NULL; END$$;
DO $$BEGIN CREATE ROLE authenticated; EXCEPTION WHEN duplicate_object THEN NULL; END$$;
DO $$BEGIN CREATE ROLE merdian_ro; EXCEPTION WHEN duplicate_object THEN NULL; END$$;
GRANT USAGE ON SCHEMA public TO anon, merdian_ro;
