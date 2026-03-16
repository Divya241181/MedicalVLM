-- Drop old policy and recreate with explicit permissions
DROP POLICY IF EXISTS "Users see own reports" ON public.report_history;

CREATE POLICY "Users can insert own reports"
  ON public.report_history
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can select own reports"
  ON public.report_history
  FOR SELECT
  USING (auth.uid() = user_id);
