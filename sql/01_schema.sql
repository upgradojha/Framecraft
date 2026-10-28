-- Run ONCE in Supabase Dashboard -> SQL Editor.
-- Supabase Auth itself manages auth.users. Do NOT manually create a users table.

-- Every creation belongs to one authenticated user.
CREATE TABLE IF NOT EXISTS public.creations (
    id VARCHAR(36) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    headline VARCHAR(140) NOT NULL DEFAULT '',
    subtitle VARCHAR(200) NOT NULL DEFAULT '',
    extra_prompt TEXT NOT NULL DEFAULT '',
    image_size VARCHAR(20) NOT NULL,
    quality VARCHAR(12) NOT NULL,
    output_format VARCHAR(8) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    reference_url TEXT NOT NULL,
    reference_file_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One creation may have multiple output images.
CREATE TABLE IF NOT EXISTS public.generated_images (
    id VARCHAR(36) PRIMARY KEY,
    creation_id VARCHAR(36) NOT NULL REFERENCES public.creations(id) ON DELETE CASCADE,
    style_name VARCHAR(30) NOT NULL,
    image_url TEXT,
    imagekit_file_id VARCHAR(100),
    status VARCHAR(12) NOT NULL CHECK (status IN ('success', 'failed')),
    error_message VARCHAR(300),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Speed up user-specific history and image lookups.
CREATE INDEX IF NOT EXISTS idx_creations_user ON public.creations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_creation ON public.generated_images(creation_id);

-- Protect tables in case they are ever accessed via Supabase REST directly.
ALTER TABLE public.creations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_images ENABLE ROW LEVEL SECURITY;

-- A signed-in user can only read or write their own creations.
DROP POLICY IF EXISTS creations_own ON public.creations;
CREATE POLICY creations_own ON public.creations FOR ALL TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));

-- Image records are accessible only if their parent creation belongs to the user.
DROP POLICY IF EXISTS images_own ON public.generated_images;
CREATE POLICY images_own ON public.generated_images FOR ALL TO authenticated
USING (EXISTS (SELECT 1 FROM public.creations c
              WHERE c.id = creation_id AND c.user_id = (SELECT auth.uid())))
WITH CHECK (EXISTS (SELECT 1 FROM public.creations c
                   WHERE c.id = creation_id AND c.user_id = (SELECT auth.uid())));

-- Note: FastAPI uses a PostgreSQL connection and ALWAYS filters by user_id.
-- Its privileged PostgreSQL connection may bypass RLS. Never send DATABASE_URL to React.
