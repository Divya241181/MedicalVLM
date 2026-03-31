CREATE TABLE public.report_history (
  id          UUID    DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID    REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  image_name  TEXT    NOT NULL,
  generated_report TEXT NOT NULL,
  bleu_score  FLOAT,
  endpoint    TEXT NOT NULL DEFAULT 'generate',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.report_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see own reports"
  ON public.report_history
  FOR ALL
  USING (auth.uid() = user_id);
