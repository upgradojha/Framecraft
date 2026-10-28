-- Simple pgAdmin queries you can explain during your college viva.
-- Replace sample UUID with the ID shown in Supabase Authentication -> Users.

-- 1. See the last ten creations.
SELECT id, user_id, prompt, model_name, created_at
FROM public.creations ORDER BY created_at DESC LIMIT 10;

-- 2. See all generated images with their styles and results.
SELECT creation_id, style_name, status, image_url
FROM public.generated_images ORDER BY created_at DESC LIMIT 20;

-- 3. Join parent and child tables to see one user's gallery.
SELECT c.prompt, c.headline, i.style_name, i.image_url, i.status
FROM public.creations AS c
JOIN public.generated_images AS i ON i.creation_id = c.id
WHERE c.user_id = 'REPLACE_WITH_REAL_USER_UUID'::uuid
ORDER BY c.created_at DESC;

-- 4. Count successful output images for each user.
SELECT c.user_id, COUNT(i.id) AS successful_images
FROM public.creations AS c
JOIN public.generated_images AS i ON i.creation_id = c.id
WHERE i.status = 'success'
GROUP BY c.user_id;

-- 5. Verify cascade relationship without deleting anything.
SELECT c.id, COUNT(i.id) AS image_count
FROM public.creations c
LEFT JOIN public.generated_images i ON i.creation_id = c.id
GROUP BY c.id;
