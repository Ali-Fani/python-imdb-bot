-- Update rating range from 0-10 to 1-10 scale
-- Drop existing constraint and create new one
ALTER TABLE ratings DROP CONSTRAINT IF EXISTS ratings_rating_check;
ALTER TABLE ratings ADD CONSTRAINT ratings_rating_check CHECK (rating >= 1 AND rating <= 10);

-- Update any existing ratings of 0 to 1 (if any)
UPDATE ratings SET rating = 1 WHERE rating = 0;

-- Add comment to document the rating scale
COMMENT ON COLUMN ratings.rating IS 'Rating value from 1 to 10 (1-10 scale)';